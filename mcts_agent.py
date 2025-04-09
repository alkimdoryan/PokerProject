import random
import math
import copy
from treys import Card as TreysCard, Evaluator

from poker import Player

class MCTSNode:
    def __init__(self, game_state, parent=None, action=None):
        self.game_state = game_state
        self.parent = parent
        self.action = action  # Bu düğüme gelmek için yapılan aksiyon
        self.children = []
        self.visits = 0
        self.wins = 0
        self.untried_actions = self.get_possible_actions()
        
    def get_possible_actions(self):
        # Mevcut durumda yapılabilecek aksiyonlar
        return ["fold", "call", "raise"]
        
    def select_child(self):
        # UCB1 formülüne göre en iyi çocuğu seç
        # UCB1 = wins/visits + C * sqrt(2 * ln(parent_visits) / visits)
        C = 1.414  # Exploration parametresi (sqrt(2))
        
        best_score = -float('inf')
        best_child = None
        
        for child in self.children:
            # UCB1 formülü
            exploitation = child.wins / child.visits if child.visits > 0 else 0
            exploration = math.sqrt(2 * math.log(self.visits) / child.visits) if child.visits > 0 else float('inf')
            score = exploitation + C * exploration
            
            if score > best_score:
                best_score = score
                best_child = child
                
        return best_child
        
    def add_child(self, action, game_state):
        # Yeni bir çocuk düğüm ekle
        child = MCTSNode(game_state, self, action)
        self.untried_actions.remove(action)
        self.children.append(child)
        return child
        
    def update(self, result):
        # Düğümü simülasyon sonucuna göre güncelle
        self.visits += 1
        self.wins += result
        
    def is_fully_expanded(self):
        # Tüm aksiyonlar denenmiş mi
        return len(self.untried_actions) == 0
        
    def is_terminal(self):
        # Oyun durumu terminal mi (oyun bitti mi)
        # Tüm oyuncular fold yaptıysa veya showdown aşamasındaysa
        return self.game_state.is_terminal()

class MCTSAgent(Player):
    def __init__(self, name, stack, simulation_count=1000):
        super().__init__(name, stack)
        self.simulation_count = simulation_count
        self.evaluator = Evaluator()
        
    def get_action(self, game_state):
        # Monte Carlo Tree Search ile en iyi aksiyonu seç
        root = MCTSNode(copy.deepcopy(game_state))
        
        # MCTS döngüsü
        for i in range(self.simulation_count):
            # 1. Selection: En iyi düğümü seç
            node = self.select(root)
            
            # 2. Expansion: Yeni bir düğüm ekle
            if not node.is_terminal() and node.is_fully_expanded():
                node = self.expand(node)
                
            # 3. Simulation: Oyunu simüle et
            result = self.simulate(node)
            
            # 4. Backpropagation: Sonucu yukarı doğru yay
            self.backpropagate(node, result)
            
        # En çok ziyaret edilen çocuğun aksiyonunu seç
        if not root.children:
            # Eğer hiç çocuk düğüm yoksa, varsayılan olarak "call" aksiyonunu döndür
            return "call"
            
        best_child = self.best_child(root)
        return best_child.action
    
    def get_raise_amount(self, game_state):
        # Monte Carlo Tree Search ile en iyi raise miktarını seç
        # Şimdilik basit bir heuristik kullanalım: pot'un %75'i
        needed_to_call = game_state.current_bet - self.bet
        raise_amount = needed_to_call + int(0.75 * game_state.pot)
        
        # Raise miktarı stack'ten büyük olamaz
        raise_amount = min(raise_amount, self.stack)
        
        return raise_amount
    
    def select(self, node):
        # En iyi düğümü seç
        while not node.is_terminal() and node.is_fully_expanded():
            node = node.select_child()
        return node
    
    def expand(self, node):
        # Yeni bir düğüm ekle
        action = random.choice(node.untried_actions)
        new_game_state = self.simulate_action(node.game_state, action)
        return node.add_child(action, new_game_state)
    
    def simulate(self, node):
        # Oyunu simüle et
        game_state = copy.deepcopy(node.game_state)
        
        # Rakip kartlarını rastgele ata (kısmi bilgi modellemesi)
        self.assign_random_cards(game_state)
        
        # Oyunu sonuna kadar rastgele oyna
        while not game_state.is_terminal():
            possible_actions = ["fold", "call", "raise"]
            action = random.choice(possible_actions)
            game_state = self.simulate_action(game_state, action)
        
        # Sonucu hesapla
        return self.calculate_result(game_state)
    
    def backpropagate(self, node, result):
        # Sonucu yukarı doğru yay
        while node is not None:
            node.update(result)
            node = node.parent
    
    def best_child(self, node):
        # En çok ziyaret edilen çocuğu seç
        if not node.children:
            return None
        return max(node.children, key=lambda c: c.visits)
    
    def simulate_action(self, game_state, action):
        # Aksiyonu simüle et
        new_game_state = copy.deepcopy(game_state)
        current_player = new_game_state.get_current_player()
        
        # Aksiyonu uygula
        if action == "fold":
            # Fold aksiyonu - oyuncu eli bırakır
            current_player.is_folded = True
        elif action == "call":
            # Call aksiyonu - mevcut bet kadar çağırır
            call_amount = new_game_state.current_bet - current_player.bet
            if call_amount > 0:
                current_player.stack -= call_amount
                current_player.bet += call_amount
                new_game_state.pot += call_amount
        elif action == "raise":
            # Raise aksiyonu - yeni bet miktarı
            raise_amount = self.get_raise_amount(new_game_state)
            current_player.stack -= raise_amount
            current_player.bet += raise_amount
            new_game_state.current_bet = current_player.bet
            new_game_state.pot += raise_amount
        
        # Bir sonraki oyuncuya geç
        new_game_state.next_player()
        
        return new_game_state
    
    def assign_random_cards(self, game_state):
        # Rakip kartlarını rastgele ata
        # Önce mevcut dağıtılmış kartları belirle (elimizde ve masada olanlar)
        used_cards = []
        
        # Bizim kartlarımız
        for card in self.hand:
            used_cards.append(card)
        
        # Masa kartları
        for card in game_state.community_cards:
            used_cards.append(card)
        
        # Diğer oyuncuların kartları (eğer biliyorsak)
        for player in game_state.players:
            if player.id != self.id and not player.is_folded:
                # Her oyuncuya 2 rastgele kart ver
                available_cards = [card for card in game_state.deck.cards if card not in used_cards]
                if len(available_cards) >= 2:
                    player_cards = random.sample(available_cards, 2)
                    player.hand = player_cards
                    used_cards.extend(player_cards)
    
    def calculate_result(self, game_state):
        # Oyun sonucunu hesapla (kazanç veya kayıp)
        if self.is_folded:
            # Fold yaptıysak kaybettik
            return -1
        
        # Showdown (el değerlendirme) yapıyoruz
        active_players = [p for p in game_state.players if not p.is_folded]
        
        # Sadece bir oyuncu kaldıysa, o kazanır
        if len(active_players) == 1:
            return 1 if active_players[0].id == self.id else -1
        
        # Birden fazla oyuncu kaldıysa, el gücüne göre kazananı belirle
        player_scores = []
        for player in active_players:
            score = self.calculate_hand_score(player.hand, game_state.community_cards)
            player_scores.append((player, score))
        
        # En düşük skor en iyi el (treys'te 1 en iyi, 7462 en kötü)
        player_scores.sort(key=lambda x: x[1])
        winner = player_scores[0][0]
        
        return 1 if winner.id == self.id else -1
    
    def calculate_hand_score(self, hole_cards, community_cards):
        # Treys evaluator kullanarak el skorunu hesapla
        evaluator = Evaluator()
        
        # Kartları Treys formatına dönüştür
        treys_hole_cards = []
        for card in hole_cards:
            suit_map = {"spades": "s", "hearts": "h", "diamonds": "d", "clubs": "c"}
            rank_map = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", 
                       "9": "9", "10": "T", "jack": "J", "queen": "Q", "king": "K", "ace": "A"}
            
            card_str = rank_map.get(card.rank, "") + suit_map.get(card.suit, "")
            treys_card = TreysCard.new(card_str)
            treys_hole_cards.append(treys_card)
        
        treys_community_cards = []
        for card in community_cards:
            suit_map = {"spades": "s", "hearts": "h", "diamonds": "d", "clubs": "c"}
            rank_map = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", 
                       "9": "9", "10": "T", "jack": "J", "queen": "Q", "king": "K", "ace": "A"}
            
            card_str = rank_map.get(card.rank, "") + suit_map.get(card.suit, "")
            treys_card = TreysCard.new(card_str)
            treys_community_cards.append(treys_card)
        
        # El skorunu hesapla (1 en iyi, 7462 en kötü)
        score = evaluator.evaluate(treys_community_cards, treys_hole_cards)
        return score
    
    # Yardımcı fonksiyonlar
    def is_folded(self, player_id, game_state):
        for player in game_state.players:
            if player.id == player_id:
                return player.is_folded
        return False 