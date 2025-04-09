import random
import copy
from enum import Enum
from treys import Card as TreysCard, Evaluator

from poker import Player

class NodeType(Enum):
    MAX = 1      # Bizim hamlemiz
    MIN = 2      # Rakip hamlesi
    CHANCE = 3   # Kartların dağıtımı

class ExpectiminimaxNode:
    def __init__(self, game_state, node_type, depth, player_id=None, parent_action=None):
        self.game_state = game_state
        self.node_type = node_type
        self.depth = depth
        self.player_id = player_id  # MAX node için oyuncu ID'si
        self.parent_action = parent_action  # Bu düğüme gelmek için yapılan aksiyon
        self.children = []
        
    def get_possible_actions(self):
        # Mevcut durumda yapılabilecek aksiyonlar
        return ["fold", "call", "raise"]
        
    def is_terminal(self):
        # Oyun durumu terminal mi (oyun bitti mi)
        # Tüm oyuncular fold yaptıysa veya showdown aşamasındaysa
        return self.game_state.is_terminal() or self.depth <= 0

class ExpectiminimaxAgent(Player):
    def __init__(self, name, stack, max_depth=3):
        super().__init__(name, stack)
        self.max_depth = max_depth
        self.evaluator = Evaluator()
        self.player_id = None  # Oyun başladığında atanacak
        
    def get_action(self, game_state):
        # Expectiminimax algoritması ile en iyi aksiyonu seç
        try:
            self.player_id = game_state.current_player_id
            root = ExpectiminimaxNode(copy.deepcopy(game_state), NodeType.MAX, self.max_depth, self.player_id)
            
            # Her bir aksiyonun değerini hesapla
            best_value = -float('inf')
            best_action = "fold"  # Varsayılan aksiyon
            
            for action in root.get_possible_actions():
                new_game_state = self.simulate_action(root.game_state, action)
                
                # Aksiyonu değerlendir
                if action == "fold":
                    # Fold aksiyonu - Pot'u kaybederiz, stack değişmez
                    value = self.evaluate_folding(new_game_state)
                else:
                    # Call veya raise aksiyonu - Expectiminimax değerini hesapla
                    next_node_type = NodeType.MIN if new_game_state.current_player_id != self.player_id else NodeType.MAX
                    child = ExpectiminimaxNode(new_game_state, next_node_type, self.max_depth-1, new_game_state.current_player_id, action)
                    value = self.expectiminimax(child)
                
                # En iyi aksiyonu seç
                if value > best_value:
                    best_value = value
                    best_action = action
                    
            return best_action
        except Exception as e:
            # Herhangi bir hata durumunda güvenli bir varsayılan aksiyon döndür
            print(f"ExpectiminimaxAgent hatası: {e}")
            return "call"
    
    def get_raise_amount(self, game_state):
        # Basit bir heuristik: pot'un %60'ı
        needed_to_call = game_state.current_bet - self.bet
        raise_amount = needed_to_call + int(0.6 * game_state.pot)
        
        # Raise miktarı stack'ten büyük olamaz
        raise_amount = min(raise_amount, self.stack)
        
        return raise_amount
    
    def expectiminimax(self, node):
        # Terminal düğüm mü kontrol et
        if node.is_terminal():
            return self.evaluate_terminal(node.game_state)
            
        # Düğüm tipine göre farklı hesapla
        if node.node_type == NodeType.MAX:
            # En yüksek değeri seç (bizim hamlemiz)
            value = -float('inf')
            
            for action in node.get_possible_actions():
                new_game_state = self.simulate_action(node.game_state, action)
                next_node_type = NodeType.MIN if new_game_state.current_player_id != self.player_id else NodeType.MAX
                child = ExpectiminimaxNode(new_game_state, next_node_type, node.depth-1, new_game_state.current_player_id, action)
                value = max(value, self.expectiminimax(child))
                
            return value
            
        elif node.node_type == NodeType.MIN:
            # En düşük değeri seç (rakip hamlesi)
            value = float('inf')
            
            for action in node.get_possible_actions():
                new_game_state = self.simulate_action(node.game_state, action)
                
                # Bir sonraki kart açılacaksa CHANCE, değilse MAX/MIN
                if self.is_next_community_card(new_game_state):
                    next_node_type = NodeType.CHANCE
                else:
                    next_node_type = NodeType.MAX if new_game_state.current_player_id == self.player_id else NodeType.MIN
                    
                child = ExpectiminimaxNode(new_game_state, next_node_type, node.depth-1, new_game_state.current_player_id, action)
                value = min(value, self.expectiminimax(child))
                
            return value
            
        else:  # NodeType.CHANCE
            # Olası kart çekimlerinin beklenen değerini hesapla
            value = 0
            num_scenarios = min(5, node.depth*2)  # Hesaplama maliyeti için sınırlı sayıda senaryo
            
            for _ in range(num_scenarios):
                new_game_state = copy.deepcopy(node.game_state)
                self.simulate_next_community_card(new_game_state)
                
                next_node_type = NodeType.MAX if new_game_state.current_player_id == self.player_id else NodeType.MIN
                child = ExpectiminimaxNode(new_game_state, next_node_type, node.depth-1, new_game_state.current_player_id)
                
                # Her senaryonun eşit olasılığı var
                value += self.expectiminimax(child) / num_scenarios
                
            return value
    
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
    
    def is_next_community_card(self, game_state):
        # Bir sonraki aşamada community card açılacak mı
        # Bahis turu tamamlandıysa ve henüz 5 kart açılmadıysa
        if game_state.is_betting_round_done() and len(game_state.community_cards) < 5:
            return True
            
        # Flop öncesiyse (preflop aşaması bitmiş)
        if len(game_state.community_cards) == 0 and game_state.is_preflop_done():
            return True
            
        # Turn öncesiyse (flop aşaması bitmiş)
        if len(game_state.community_cards) == 3 and game_state.is_flop_done():
            return True
            
        # River öncesiyse (turn aşaması bitmiş)
        if len(game_state.community_cards) == 4 and game_state.is_turn_done():
            return True
            
        return False
    
    def simulate_next_community_card(self, game_state):
        # Bir sonraki community card'ı simüle et
        # Önce mevcut dağıtılmış kartları belirle
        used_cards = []
        
        # Oyuncuların elindeki kartlar
        for player in game_state.players:
            for card in player.hand:
                used_cards.append(card)
        
        # Masa kartları
        for card in game_state.community_cards:
            used_cards.append(card)
        
        # Kullanılmayan kartlardan rastgele seç
        available_cards = [card for card in game_state.deck.cards if card not in used_cards]
        
        # Flop (3 kart)
        if len(game_state.community_cards) == 0:
            if len(available_cards) >= 3:
                flop_cards = random.sample(available_cards, 3)
                game_state.community_cards.extend(flop_cards)
        # Turn (1 kart)
        elif len(game_state.community_cards) == 3:
            if len(available_cards) >= 1:
                turn_card = random.choice(available_cards)
                game_state.community_cards.append(turn_card)
        # River (1 kart)
        elif len(game_state.community_cards) == 4:
            if len(available_cards) >= 1:
                river_card = random.choice(available_cards)
                game_state.community_cards.append(river_card)
                
    def evaluate_terminal(self, game_state):
        # Terminal düğümün değerini hesapla
        if self.is_showdown(game_state):
            # Showdown - el gücüne göre değerlendir
            hand_score = self.calculate_hand_score(self.hand, game_state.community_cards)
            return self.convert_hand_score_to_value(hand_score)
        else:
            # Fold durumu - kalan oyuncu sayısına göre değerlendir
            return self.evaluate_non_showdown(game_state)
    
    def evaluate_folding(self, game_state):
        # Fold aksiyonunun değerini hesapla
        # Bu genellikle en kötü değerdir, çünkü pot'u kaybederiz
        return -game_state.pot
    
    def is_showdown(self, game_state):
        # Showdown aşamasında mıyız
        return len(game_state.community_cards) == 5 and not game_state.is_terminal()
    
    def evaluate_non_showdown(self, game_state):
        # Fold durumunda değerlendirme
        # Eğer sadece biz kaldıysak kazanırız, değilse kaybederiz
        if game_state.is_last_player_standing(self.player_id):
            return game_state.pot
        else:
            return -self.bet
    
    def convert_hand_score_to_value(self, hand_score):
        # El skorunu (1-7462) değere dönüştür
        # 1 en iyi, 7462 en kötü
        # Değer aralığı: [-1, 1]
        normalized_score = 1.0 - (hand_score / 7462.0) * 2.0
        return normalized_score
    
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
    
    def is_folded(self, player_id, game_state):
        for player in game_state.players:
            if player.id == player_id:
                return player.is_folded
        return False 