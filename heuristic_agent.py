import random
from treys import Card as TreysCard, Evaluator

from poker import Player

class BasicHeuristicAgent(Player):
    def __init__(self, name, stack):
        super().__init__(name, stack)
        self.bluff_chance = 0.05
        self.alpha = 0.5  # Pot odaklı raise çarpanı
        
    def get_action(self, game_state):
        # Blöf yapacak mıyız kontrol et
        if random.random() < self.bluff_chance:
            return "raise"
            
        # Preflop/postflop ayrımı
        if len(game_state.community_cards) == 0:
            # Preflop karar mantığı
            rank_sum = self.calculate_rank_sum()
            
            if rank_sum >= 20:
                return "raise"
            elif 15 <= rank_sum < 20:
                return "call"
            else:
                return "fold"
        else:
            # Postflop karar mantığı
            hand_score = self.calculate_hand_score(game_state)
            
            if hand_score < 2000:
                return "raise"
            elif hand_score < 4000:
                return "call"
            else:
                # Eğer call bedava ise (current_bet == player.bet), call yap
                if game_state.current_bet == self.bet:
                    return "call"  # Bu durumda "check" yapmış oluyoruz
                else:
                    return "fold"
    
    def get_raise_amount(self, game_state):
        # Pot odaklı raise miktarı
        needed_to_call = game_state.current_bet - self.bet
        raise_amount = needed_to_call + int(self.alpha * game_state.pot)
        
        # Raise miktarı stack'ten büyük olamaz
        raise_amount = min(raise_amount, self.stack)
        
        return raise_amount
            
    def calculate_rank_sum(self):
        # İki hole kartın rank toplamını hesapla
        rank_values = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, 
                      "jack": 11, "queen": 12, "king": 13, "ace": 14}
        
        rank_sum = 0
        for card in self.hand:
            rank_sum += rank_values.get(card.rank, 0)
            
        return rank_sum
        
    def calculate_hand_score(self, game_state):
        # Treys evaluator kullanarak el skorunu hesapla
        evaluator = Evaluator()
        
        # Kartları Treys formatına dönüştür
        hole_cards = []
        for card in self.hand:
            suit_map = {"spades": "s", "hearts": "h", "diamonds": "d", "clubs": "c"}
            rank_map = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", 
                       "9": "9", "10": "T", "jack": "J", "queen": "Q", "king": "K", "ace": "A"}
            
            card_str = rank_map.get(card.rank, "") + suit_map.get(card.suit, "")
            treys_card = TreysCard.new(card_str)
            hole_cards.append(treys_card)
        
        community_cards = []
        for card in game_state.community_cards:
            suit_map = {"spades": "s", "hearts": "h", "diamonds": "d", "clubs": "c"}
            rank_map = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", 
                       "9": "9", "10": "T", "jack": "J", "queen": "Q", "king": "K", "ace": "A"}
            
            card_str = rank_map.get(card.rank, "") + suit_map.get(card.suit, "")
            treys_card = TreysCard.new(card_str)
            community_cards.append(treys_card)
        
        # El skorunu hesapla (1 en iyi, 7462 en kötü)
        score = evaluator.evaluate(community_cards, hole_cards)
        return score

class AggressiveHeuristicAgent(Player):
    def __init__(self, name, stack):
        super().__init__(name, stack)
        self.bluff_chance = 0.15  # Daha yüksek blöf şansı
        self.alpha = 0.8  # Daha yüksek pot odaklı raise çarpanı
        
    def get_action(self, game_state):
        # Blöf yapacak mıyız kontrol et
        if random.random() < self.bluff_chance:
            return "raise"
            
        # Preflop/postflop ayrımı
        if len(game_state.community_cards) == 0:
            # Preflop karar mantığı - daha agresif
            rank_sum = self.calculate_rank_sum()
            
            if rank_sum >= 18:  # Daha düşük eşik
                return "raise"
            elif 12 <= rank_sum < 18:  # Daha düşük eşik
                return "call"
            else:
                # Zayıf ellerle bile %20 ihtimalle call
                if random.random() < 0.2:
                    return "call"
                else:
                    return "fold"
        else:
            # Postflop karar mantığı - daha agresif
            hand_score = self.calculate_hand_score(game_state)
            
            if hand_score < 3000:  # Daha yüksek eşik
                return "raise"
            elif hand_score < 5000:  # Daha yüksek eşik
                return "call"
            else:
                # Kötü elle bile %30 ihtimalle call, diğer durumlarda fold
                if random.random() < 0.3 or game_state.current_bet == self.bet:
                    return "call"
                else:
                    return "fold"
    
    def get_raise_amount(self, game_state):
        # Pot odaklı raise miktarı - daha yüksek
        needed_to_call = game_state.current_bet - self.bet
        raise_amount = needed_to_call + int(self.alpha * game_state.pot)
        
        # Raise miktarı stack'ten büyük olamaz
        raise_amount = min(raise_amount, self.stack)
        
        return raise_amount
            
    def calculate_rank_sum(self):
        # İki hole kartın rank toplamını hesapla
        rank_values = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8, "9": 9, "10": 10, 
                      "jack": 11, "queen": 12, "king": 13, "ace": 14}
        
        rank_sum = 0
        for card in self.hand:
            rank_sum += rank_values.get(card.rank, 0)
            
        return rank_sum
        
    def calculate_hand_score(self, game_state):
        # Treys evaluator kullanarak el skorunu hesapla
        evaluator = Evaluator()
        
        # Kartları Treys formatına dönüştür
        hole_cards = []
        for card in self.hand:
            suit_map = {"spades": "s", "hearts": "h", "diamonds": "d", "clubs": "c"}
            rank_map = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", 
                       "9": "9", "10": "T", "jack": "J", "queen": "Q", "king": "K", "ace": "A"}
            
            card_str = rank_map.get(card.rank, "") + suit_map.get(card.suit, "")
            treys_card = TreysCard.new(card_str)
            hole_cards.append(treys_card)
        
        community_cards = []
        for card in game_state.community_cards:
            suit_map = {"spades": "s", "hearts": "h", "diamonds": "d", "clubs": "c"}
            rank_map = {"2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", 
                       "9": "9", "10": "T", "jack": "J", "queen": "Q", "king": "K", "ace": "A"}
            
            card_str = rank_map.get(card.rank, "") + suit_map.get(card.suit, "")
            treys_card = TreysCard.new(card_str)
            community_cards.append(treys_card)
        
        # El skorunu hesapla (1 en iyi, 7462 en kötü)
        score = evaluator.evaluate(community_cards, hole_cards)
        return score 