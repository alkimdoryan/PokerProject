import random
from treys import Card, Evaluator

class Card:
    def __init__(self, suit, rank):
        self.suit = suit
        self.rank = rank
        
    def __str__(self):
        return f"{self.rank}_of_{self.suit}"

class Deck:
    def __init__(self):
        suits = ["spades", "hearts", "diamonds", "clubs"]
        ranks = ["ace", "2", "3", "4", "5", "6", "7", "8", "9", "10", "jack", "queen", "king"] 
        self.cards = [Card(suit, rank) for suit in suits for rank in ranks]
        
    def shuffle(self):
        random.shuffle(self.cards)
        
    def deal(self, num_cards):
        dealt_cards = []
        for i in range(num_cards):
            if len(self.cards) > 0:
                card = self.cards.pop()
                dealt_cards.append(card)
        return dealt_cards

class Player:
    def __init__(self, name, stack):
        self.name = name
        self.stack = stack
        self.hand = []
        self.bet = 0
        self.is_folded = False
        self.is_human = False
        self.id = None  # Oyuncu ID'si
        
    def add_cards(self, cards):
        self.hand.extend(cards)
        
    def remove_card(self, card):
        self.hand.remove(card)
        
    def get_hand(self):
        return self.hand
    
    def place_bet(self, amount):
        self.bet += amount
        self.stack -= amount
        
    def fold(self):
        self.is_folded = True
        
    def reset(self):
        self.hand = []
        self.bet = 0
        self.is_folded = False
        
    def get_action(self, game):
        # Varsayılan aksiyon: rastgele
        return random.choice(["fold", "call", "raise"])
    
    def get_raise_amount(self, game):
        # Varsayılan raise miktarı: minimum raise (2 * small blind)
        return game.small_blind * 2

class PokerGame:
    def __init__(self, player_names, player_types, starting_stack, max_round, small_blind):
        self.deck = Deck()
        self.players = [Player(name, starting_stack) for name in player_names]
        # Oyunculara ID ata
        for i, player in enumerate(self.players):
            player.id = i
        self.player_types = player_types
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        self.round = 0
        self.max_round = max_round
        self.small_blind = small_blind
        self.current_player_id = 0  # Mevcut oyuncunun ID'si
        
    def deal_hole_cards(self):
        for player in self.players:
            cards = self.deck.deal(2)
            player.add_cards(cards)
            
    def deal_community_cards(self, num_cards):
        cards = self.deck.deal(num_cards)
        self.community_cards.extend(cards)
        
    def place_bet(self, player, amount):
        player.place_bet(amount)
        self.current_bet = max(self.current_bet, player.bet)
        self.pot += amount
        
    def reset_round(self):
        self.deck = Deck()
        self.deck.shuffle()
        self.community_cards = []
        self.pot = 0
        self.current_bet = 0
        for player in self.players:
            player.reset()
            
    def remove_bankrupt_players(self):
        """Chip'i 0 olan oyuncuları oyundan çıkar"""
        bankrupt_players = [player for player in self.players if player.stack <= 0]
        for player in bankrupt_players:
            self.players.remove(player)
        return len(bankrupt_players) > 0  # Oyuncu çıkarıldı mı
        
    def play_round(self):
        self.reset_round()
        self.deal_hole_cards()
        
        # Preflop
        self.place_bet(self.players[0], self.small_blind)
        self.place_bet(self.players[1], self.small_blind * 2)
        self.betting_round()
        
        # Flop
        self.deal_community_cards(3)
        self.betting_round()
        
        # Turn
        self.deal_community_cards(1)
        self.betting_round()
        
        # River
        self.deal_community_cards(1)
        self.betting_round()
        
        # Showdown
        self.showdown()
        
    def betting_round(self):
        # Bahis turunu yönet
        current_player = self.players[0]
        while not self.is_betting_round_done():
            if not current_player.is_folded:
                action = current_player.get_action(self)
                if action == "fold":
                    current_player.fold()
                elif action == "call":
                    self.place_bet(current_player, self.current_bet - current_player.bet)
                elif action == "raise":
                    raise_amount = current_player.get_raise_amount(self)
                    self.place_bet(current_player, raise_amount)
            current_player = self.get_next_player(current_player)
            
    def is_betting_round_done(self):
        """Bahis turu tamamlandı mı kontrol et"""
        active_players = [p for p in self.players if not p.is_folded]
        
        # Sadece bir oyuncu kaldıysa tur tamamlanmıştır
        if len(active_players) <= 1:
            return True
        
        # Tüm aktif oyuncuların bahisleri eşit olmalı
        # Önce tüm bahislerin aynı olup olmadığını kontrol et
        bet_values = set()
        for player in active_players:
            if player.stack > 0:  # All-in olmayan oyuncular için
                bet_values.add(player.bet)
            # All-in oyuncular için kontrole gerek yok
        
        # Eğer bahisler eşit değilse, tur bitmemiştir
        if len(bet_values) > 1:
            return False
            
        # Eğer buraya kadar geldiyse, tüm bahisler eşittir
        # Bu durumda da, tüm aktif oyuncuların aksiyon aldığından emin olmalıyız
        # Bu kontrol ui.py içerisinde yapılacak
            
        return True
    
    def get_next_player(self, player):
        # Sıradaki oyuncuyu döndür
        player_index = self.players.index(player)
        for i in range(1, len(self.players)):
            next_player_index = (player_index + i) % len(self.players)
            if not self.players[next_player_index].is_folded:
                return self.players[next_player_index]
        return None
    
    def showdown(self):
        # Kazanan eli belirle ve potları dağıt
        if self.is_game_over():
            return
        
        players_in_showdown = [player for player in self.players if not player.is_folded]
        
        if len(players_in_showdown) == 1:
            winner = players_in_showdown[0]
        else:
            scores = [(player, el_gucu_hesapla(player.hand, self.community_cards)) for player in players_in_showdown]
            winner = min(scores, key=lambda x: x[1])[0]
            
        winner.stack += self.pot
        self.pot = 0
        
    def is_game_over(self):
        # Oyun bitti mi kontrol et
        players_in_game = [player for player in self.players if not player.is_folded]
        return len(players_in_game) == 1
    
    def is_terminal(self):
        # Oyun durumu terminal mi (oyun bitti mi)
        # 1. Tüm oyuncular fold yaptıysa
        active_players = [player for player in self.players if not player.is_folded]
        if len(active_players) <= 1:
            return True
        
        # 2. Showdown aşaması tamamlanmışsa (5 community card açılmış ve son bahis turu bitmiş)
        if len(self.community_cards) == 5 and self.is_betting_round_done():
            return True
            
        return False
        
    def is_preflop_done(self):
        # Preflop aşaması tamamlandı mı
        return len(self.community_cards) == 0 and self.is_betting_round_done()
        
    def is_flop_done(self):
        # Flop aşaması tamamlandı mı
        return len(self.community_cards) == 3 and self.is_betting_round_done()
        
    def is_turn_done(self):
        # Turn aşaması tamamlandı mı
        return len(self.community_cards) == 4 and self.is_betting_round_done()
        
    def get_current_player(self):
        # Mevcut oyuncuyu döndür
        return self.players[self.current_player_id]
        
    def next_player(self):
        # Bir sonraki oyuncuya geç
        found = False
        while not found:
            self.current_player_id = (self.current_player_id + 1) % len(self.players)
            if not self.players[self.current_player_id].is_folded:
                found = True
        return self.players[self.current_player_id]
        
    def is_last_player_standing(self, player_id):
        # Belirli bir oyuncu son aktif oyuncu mu kontrol et
        active_players = [player for player in self.players if not player.is_folded]
        if len(active_players) == 1 and active_players[0].id == player_id:
            return True
        return False

def el_gucu_hesapla(hole_cards, community_cards):
    # treys kütüphanesini kullanarak el gücünü hesapla
    from treys import Card as TreysCard, Evaluator
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

