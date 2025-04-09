import sys
import os
import argparse
import json
import time
from datetime import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from collections import defaultdict
import logging

from poker import PokerGame, Player
from heuristic_agent import BasicHeuristicAgent, AggressiveHeuristicAgent
from mcts_agent import MCTSAgent
from expectiminimax_agent import ExpectiminimaxAgent

# Logging ayarları
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def create_agent(agent_type, name, stack):
    """Belirtilen tipte bir AI agent oluşturur"""
    if agent_type == "basic_heuristic":
        return BasicHeuristicAgent(name, stack)
    elif agent_type == "aggressive_heuristic":
        return AggressiveHeuristicAgent(name, stack)
    elif agent_type == "mcts":
        return MCTSAgent(name, stack)
    elif agent_type == "expectiminimax":
        return ExpectiminimaxAgent(name, stack)
    else:
        # Bilinmeyen agent tipi için varsayılan Player
        return Player(name, stack)

def run_ai_comparison(agent_types, num_games, starting_stack, max_round, small_blind, output_file):
    """AI agentların performansını karşılaştırır ve sonuçları bir dosyaya yazar"""
    print(f"AI Performans Karşılaştırması Başlıyor...")
    print(f"Agent Tipleri: {', '.join(agent_types)}")
    print(f"Oyun Sayısı: {num_games}")
    print(f"Her biri {max_round} el, {starting_stack} chip başlangıç ile oynanacak.")
    
    # Sonuçları toplamak için bir sözlük
    results = {
        "config": {
            "agent_types": agent_types,
            "num_games": num_games,
            "starting_stack": starting_stack,
            "max_round": max_round,
            "small_blind": small_blind
        },
        "games": [],
        "summary": {
            "wins": {agent_type: 0 for agent_type in agent_types},
            "avg_stack": {agent_type: 0 for agent_type in agent_types},
            "total_stack": {agent_type: 0 for agent_type in agent_types}
        }
    }
    
    start_time = time.time()
    
    # Oyunları çalıştır
    for game_num in range(num_games):
        print(f"Oyun {game_num+1}/{num_games} oynanıyor...")
        
        # Oyuncuları oluştur
        player_names = [f"AI-{i+1}-{agent_type}" for i, agent_type in enumerate(agent_types)]
        player_types = agent_types.copy()
        
        # Oyun nesnesini oluştur
        game = PokerGame(player_names, player_types, starting_stack, max_round, small_blind)
        
        # Oyuncuları AI agentlar ile değiştir
        game.players = []
        for i, agent_type in enumerate(agent_types):
            agent = create_agent(agent_type, f"AI-{i+1}-{agent_type}", starting_stack)
            agent.is_human = False
            agent.id = i  # ID ata
            game.players.append(agent)
        
        # El takibi
        current_round = 0
        
        # Tüm elleri oyna
        while current_round < max_round:
            current_round += 1
            game.round = current_round
            
            # Eğer 0. el ise sonraki ele geç
            if game.round == 0:
                continue
            
            # Aktif oyuncuları belirle (Stack > 0)
            active_players = [p for p in game.players if p.stack > 0]
            if len(active_players) <= 1:
                break  # Yeterli aktif oyuncu yoksa oyunu bitir
                
            # Önceki eli temizle
            game.reset_round()
            
            # Oyuncuların all-in durumlarını temizle
            for player in game.players:
                if player.stack <= 0:
                    player.is_folded = True  # Stack 0 olanlar fold olsun
                else:
                    player.is_folded = False  # Diğerleri aktif
            
            # Desteyi karıştır ve kartları dağıt
            game.deck.shuffle()
            game.deal_hole_cards()
            
            # Aktif oyuncular arasından dealer, small blind ve big blind pozisyonlarını belirle
            active_count = len(active_players)
            dealer_idx = current_round % active_count
            sb_idx = (dealer_idx + 1) % active_count
            bb_idx = (dealer_idx + 2) % active_count
            
            # Small blind ve big blind oyuncularını al
            small_blind_player = active_players[sb_idx]
            big_blind_player = active_players[bb_idx]
            
            # Small blind
            small_blind_amount = min(small_blind, small_blind_player.stack)
            game.place_bet(small_blind_player, small_blind_amount)
            
            # Big blind
            big_blind_amount = min(small_blind * 2, big_blind_player.stack)
            game.place_bet(big_blind_player, big_blind_amount)
            
            # Current bet'i büyük blind olarak ayarla
            game.current_bet = big_blind_amount
            
            # Preflop - Big blind'ın yanındaki oyuncudan başla
            current_betting_idx = (bb_idx + 1) % active_count
            play_betting_round(game, active_players, current_betting_idx)
            
            # Oyun devam ediyor mu kontrol et
            if len([p for p in game.players if not p.is_folded]) <= 1:
                # Showdown - kazanan belirleme
                winner = determine_winner(game)
                if winner:
                    winner.stack += game.pot
                    game.pot = 0
                continue
            
            # Flop
            game.deal_community_cards(3)
            reset_betting_round(game)
            # Flop için dealer'dan sonraki ilk oyuncu bahis turunu başlatır
            start_idx = (dealer_idx + 1) % active_count
            play_betting_round(game, active_players, start_idx)
            
            # Oyun devam ediyor mu kontrol et
            if len([p for p in game.players if not p.is_folded]) <= 1:
                # Showdown - kazanan belirleme
                winner = determine_winner(game)
                if winner:
                    winner.stack += game.pot
                    game.pot = 0
                continue
            
            # Turn
            game.deal_community_cards(1)
            reset_betting_round(game)
            # Turn için dealer'dan sonraki ilk oyuncu bahis turunu başlatır 
            start_idx = (dealer_idx + 1) % active_count
            play_betting_round(game, active_players, start_idx)
            
            # Oyun devam ediyor mu kontrol et
            if len([p for p in game.players if not p.is_folded]) <= 1:
                # Showdown - kazanan belirleme
                winner = determine_winner(game)
                if winner:
                    winner.stack += game.pot
                    game.pot = 0
                continue
            
            # River
            game.deal_community_cards(1)
            reset_betting_round(game)
            # River için dealer'dan sonraki ilk oyuncu bahis turunu başlatır
            start_idx = (dealer_idx + 1) % active_count
            play_betting_round(game, active_players, start_idx)
            
            # Showdown
            process_showdown(game)
            
            # Her durumda potun sıfırlandığından emin ol
            if game.pot > 0:
                active_players = [p for p in game.players if not p.is_folded]
                if active_players:
                    winner = active_players[0]
                    winner.stack += game.pot
                game.pot = 0
        
        # Sonuçları kaydet
        game_result = {
            "game_number": game_num + 1,
            "results": []
        }
        
        max_stack = 0
        winner = None
        
        for i, player in enumerate(game.players):
            agent_type = agent_types[i]
            game_result["results"].append({
                "agent_type": agent_type,
                "name": player.name,
                "final_stack": player.stack
            })
            
            results["summary"]["total_stack"][agent_type] += player.stack
            
            if player.stack > max_stack:
                max_stack = player.stack
                winner = agent_type
        
        # Kazananı kaydet
        if winner:
            results["summary"]["wins"][winner] += 1
            game_result["winner"] = winner
            
        results["games"].append(game_result)
        
    # Ortalama değerleri hesapla
    for agent_type in agent_types:
        results["summary"]["avg_stack"][agent_type] = results["summary"]["total_stack"][agent_type] / num_games
    
    end_time = time.time()
    results["execution_time"] = end_time - start_time
    
    # Sonuçları yazdır
    print("\nSonuçlar:")
    print("-" * 50)
    print(f"Toplam Süre: {results['execution_time']:.2f} saniye")
    print("-" * 50)
    print("Kazanan Sayıları:")
    for agent_type, wins in results["summary"]["wins"].items():
        print(f"  {agent_type}: {wins} ({wins/num_games*100:.1f}%)")
    print("-" * 50)
    print("Ortalama Chip Miktarları:")
    for agent_type, avg_stack in results["summary"]["avg_stack"].items():
        print(f"  {agent_type}: {avg_stack:.2f}")
    print("-" * 50)
    
    # Sonuçları dosyaya yaz
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4, ensure_ascii=False)
    
    print(f"Ayrıntılı sonuçlar '{output_file}' dosyasına kaydedildi.")

def reset_betting_round(game):
    """Bahis turunu sıfırla"""
    for player in game.players:
        player.bet = 0
    game.current_bet = 0

def play_betting_round(game, active_players, start_idx=0, max_iterations=50):
    """Bir bahis turunu oyna"""
    # Bahis yapabilecek oyuncuları belirle (stack > 0 ve fold yapmamış)
    betting_players = [p for p in active_players if not p.is_folded]
    if len(betting_players) <= 1:
        return
    
    # Is Check Round - bu turda hiç bahis yapılmamışsa True
    is_check_round = all(player.bet == 0 for player in betting_players)
    
    # Bahis yapacak oyuncuların indekslerini belirle
    current_idx = start_idx % len(betting_players)
    
    # Her oyuncunun aksiyonunu izlemek için sözlük
    player_acted = {player: False for player in betting_players}
    
    # Son raise yapan oyuncuyu takip edelim
    last_raiser = None
    
    # Sonsuz döngüyü önlemek için iterasyon sayacı
    iteration_count = 0
    
    while True:
        # Maksimum iterasyon kontrolü
        iteration_count += 1
        if iteration_count > max_iterations:
            logging.warning(f"Maksimum bahis turu iterasyonu ({max_iterations}) aşıldı. Bahis turu zorla sonlandırılıyor.")
            
            # Mevcut bahisleri eşitleyerek turu sonlandır
            # Tüm oyuncuların bahislerini en yüksek bahse eşitle
            max_bet = max(p.bet for p in betting_players)
            for player in betting_players:
                if player.bet < max_bet and player.stack > 0:
                    # Yeterli stack varsa bahislerini eşitle
                    call_amount = min(max_bet - player.bet, player.stack)
                    player.stack -= call_amount
                    player.bet += call_amount
                    game.pot += call_amount
            
            # Bahis turu tamamlandı
            return
    
        # Aktif oyuncular listesini güncelle (fold olanlar çıkarılıyor)
        betting_players = [p for p in active_players if not p.is_folded]
        if len(betting_players) <= 1:
            return  # Sadece bir oyuncu kaldıysa bahis turu bitmiş
        
        # Current index kontrol
        if current_idx >= len(betting_players):
            current_idx = 0
            
        # Aktif oyuncuyu al
        player = betting_players[current_idx]
        
        # Bahis turu tamamlandı mı kontrol et - tüm aktif oyuncular aksiyon aldı mı ve tüm bahisler eşit mi
        all_acted = all(player_acted.get(p, True) for p in betting_players)
        if all_acted and is_betting_round_done(game):
            logging.debug(f"Bahis turu tamamlandı: {[(p.name, p.bet) for p in betting_players]}")
            return
                
        # Stack 0 olan oyuncular (all-in durumunda) aksiyon alamaz
        if player.stack <= 0:
            # Bu oyuncuyu acted olarak işaretle
            player_acted[player] = True
            current_idx = (current_idx + 1) % len(betting_players)
            continue
            
        action = player.get_action(game)
        logging.debug(f"{player.name} aksiyon alıyor: {action}")
        
        # Check round ise ve call veya fold gelirse check'e çevir
        if is_check_round and (action == "call" or action == "fold"):
            action = "check"
        
        if action == "fold":
            player.is_folded = True
            # Bu oyuncuyu acted olarak işaretle
            player_acted[player] = True
        elif action == "check":
            # Check - hiçbir şey yapma, sıradaki oyuncuya geç
            player_acted[player] = True
        elif action == "call":
            call_amount = game.current_bet - player.bet
            if call_amount <= 0:
                # Check - hiçbir şey yapma
                player_acted[player] = True
            elif call_amount <= player.stack:
                # Normal call
                player.stack -= call_amount
                player.bet += call_amount
                game.pot += call_amount
                player_acted[player] = True
            else:
                # All-in (stack yeterli değil)
                game.pot += player.stack
                player.bet += player.stack
                player.stack = 0
                player_acted[player] = True
        elif action == "raise":
            raise_amount = player.get_raise_amount(game)
            
            # 0 veya negatif miktarda raise yapılamaz
            if raise_amount <= 0:
                # Raise yapamayacaksa check ya da call yap
                if is_check_round:
                    # Check yap
                    player_acted[player] = True
                else:
                    # Call yap
                    call_amount = min(game.current_bet - player.bet, player.stack)
                    if call_amount > 0:
                        player.stack -= call_amount
                        player.bet += call_amount
                        game.pot += call_amount
                    player_acted[player] = True
            else:
                # Minimum raise kontrolü
                min_raise = max(game.small_blind, game.current_bet - player.bet)
                if raise_amount < min_raise:
                    raise_amount = min_raise
                    
                # Stack kontrolü
                raise_amount = min(raise_amount, player.stack)
                
                # Normal raise - call + raise
                total_amount = raise_amount + (game.current_bet - player.bet)
                player.stack -= total_amount
                player.bet = game.current_bet + raise_amount
                game.current_bet = player.bet
                game.pot += total_amount
                
                # Raise yapıldığında, diğer tüm oyuncuların tekrar aksiyon alması gerekiyor
                for p in betting_players:
                    if p != player and p.stack > 0:
                        player_acted[p] = False
                
                # Raise yapan oyuncu aksiyon aldı sayılır
                player_acted[player] = True
                
                # Son raise yapan oyuncuyu kaydet
                last_raiser = player
        
        # Stack'in 0'dan küçük olmasını engelle
        if player.stack < 0:
            player.stack = 0
            
        # Bir sonraki oyuncuya geç
        current_idx = (current_idx + 1) % len(betting_players)

def is_betting_round_done(game):
    """Bahis turu tamamlandı mı kontrol et"""
    active_players = [p for p in game.players if not p.is_folded]
    
    # Sadece bir oyuncu kaldıysa tur tamamlanmıştır
    if len(active_players) <= 1:
        logging.debug(f"Sadece bir oyuncu kaldı, tur tamamlandı")
        return True
    
    # Tüm aktif oyuncuların bahisleri eşit olmalı
    # Önce tüm bahislerin aynı olup olmadığını kontrol et
    all_in_players = [p for p in active_players if p.stack == 0]  # All-in oyuncular
    non_all_in_players = [p for p in active_players if p.stack > 0]  # All-in olmayan oyuncular
    
    # All-in olmayan oyuncuların bahislerini kontrol et
    if non_all_in_players:
        bet_values = set(p.bet for p in non_all_in_players)
        if len(bet_values) > 1:
            logging.debug(f"Bahisler eşit değil: {bet_values}")
            return False
    
    # All-in oyuncuların durumu (onların bahisleri farklı olabilir, 
    # ama non-all-in oyuncuların bahisleri kendi aralarında eşit olmalı)
    
    # All-in olmayan oyuncular varsa ve hepsinin bahisleri eşitse, 
    # all-in oyuncuların bahisleri <= non_all_in oyuncuların bahislerine olmalı
    if non_all_in_players and all_in_players:
        max_non_all_in_bet = max(p.bet for p in non_all_in_players)
        
        # All-in oyuncuların bahisleri max_non_all_in_bet'ten büyük olmamalı
        # (all-in oyuncular max_bet'ten daha fazla koyamaz, all-in olmuşlardır zaten)
        for all_in_player in all_in_players:
            if all_in_player.bet > max_non_all_in_bet:
                logging.debug(f"All-in oyuncunun bahsi ({all_in_player.bet}) non-all-in max bahsinden ({max_non_all_in_bet}) büyük")
                return False
    
    # Sadece all-in oyuncular varsa tur tamamlanmış demektir
    if all_in_players and not non_all_in_players:
        logging.debug(f"Sadece all-in oyuncular kaldı, tur tamamlandı")
        return True
        
    # Eğer buraya kadar geldiyse, tüm bahisler eşittir
    # (player_acted kontrolü play_betting_round içinde yapılıyor)
    logging.debug(f"Bahisler eşit olduğu için tur tamamlandı")
    return True

def determine_winner(game):
    """Şu anki duruma göre kazananı belirle"""
    active_players = [p for p in game.players if not p.is_folded]
    if len(active_players) == 0:
        return None
    elif len(active_players) == 1:
        return active_players[0]
    else:
        # El gücüne göre karşılaştırma
        scores = []
        for player in active_players:
            score = el_gucu_hesapla(player.hand, game.community_cards)
            scores.append((player, score))
        
        # En düşük skor en iyi el
        scores.sort(key=lambda x: x[1])
        return scores[0][0]

def process_showdown(game):
    """Showdown işlemini gerçekleştir ve kazananı belirle"""
    active_players = [p for p in game.players if not p.is_folded]
    
    # All-in kontrolü - yan pot hesaplama için gereken bilgileri toplama
    all_in_players = [p for p in active_players if p.stack == 0]
    has_all_in = len(all_in_players) > 0
    
    if len(active_players) <= 1:
        # Tek kalan oyuncu varsa pot'u ona ver
        if active_players:
            active_players[0].stack += game.pot
        game.pot = 0
        return
    
    # El değerlendirmesi
    player_hands = []
    for player in active_players:
        score = el_gucu_hesapla(player.hand, game.community_cards)
        player_hands.append((player, score))
    
    # En düşük skor en iyi eli belirtir (treys'te 1 en iyi, 7462 en kötü)
    player_hands.sort(key=lambda x: x[1])  # El gücüne göre sıralama
    
    # Yan pot hesaplama
    if has_all_in:
        calculate_side_pots(game, active_players, player_hands)
    else:
        # Normal pot hesaplama
        winner = player_hands[0][0]
        winner.stack += game.pot
        game.pot = 0

def calculate_side_pots(game, active_players, player_hands):
    """Yan pot hesaplama"""
    # Önce oyuncuları kartlarına göre sırala
    player_hand_map = {p[0]: p[1] for p in player_hands}
    
    # Oyuncuları bet miktarına göre sırala (düşükten yükseğe)
    players_by_bet = sorted(active_players, key=lambda p: p.bet)
    
    # Toplam pot ve kümülatif oyuncu grupları
    total_pot = game.pot
    remaining_pot = total_pot
    prev_bet = 0
    
    # Her bet seviyesi için pot hesapla
    for i, player in enumerate(players_by_bet):
        current_bet = player.bet
        
        # Eğer önceki bet'ten farklı bir bet seviyesi varsa, pot hesapla
        if current_bet > prev_bet:
            # Bu seviyeye kadar olan farkı hesapla
            bet_diff = current_bet - prev_bet
            # Bu seviyede pot'a katılan oyuncu sayısı
            contributing_players = players_by_bet[i:]  # Bu ve daha büyük bet yapan oyuncular
            
            # Pot miktarını hesapla
            pot_amount = bet_diff * len(contributing_players)
            pot_amount = min(pot_amount, remaining_pot)  # Toplam pottan fazla olamaz
            
            # Kalan potu güncelle
            remaining_pot -= pot_amount
            
            if pot_amount > 0:  # Sadece pozitif pot varsa
                # Bu pot seviyesinde yarışabilecek oyuncuları bul (fold olmamış)
                eligible_players = [p for p in contributing_players if not p.is_folded]
                if eligible_players:
                    # En güçlü eli olan oyuncu(lar)ı bul
                    eligible_players.sort(key=lambda p: player_hand_map.get(p, 7462))  # En düşük skor (en iyi el)
                    best_score = player_hand_map.get(eligible_players[0], 7462)
                    
                    # Aynı skora sahip oyuncuları bul (beraberlik durumu)
                    tied_winners = [p for p in eligible_players if player_hand_map.get(p, 7462) == best_score]
                    
                    # Her kazanana eşit pay ver
                    pot_share = pot_amount // len(tied_winners)
                    remainder = pot_amount % len(tied_winners)  # Kalan chipler
                    
                    for winner in tied_winners:
                        winner_share = pot_share
                        if remainder > 0:
                            winner_share += 1
                            remainder -= 1
                            
                        winner.stack += winner_share
        
        prev_bet = current_bet
                
    # Pot'u sıfırla
    game.pot = 0

def start_ui():
    """UI modunu başlatır"""
    try:
        from ui import PokerUI
        ui = PokerUI()
        ui.run()
    except ImportError:
        print("UI modülü bulunamadı. Lütfen ui.py dosyasının olduğundan emin olun.")
        sys.exit(1)

def benchmark_agents(agent_types, num_games, starting_stack, max_round, small_blind):
    """
    Belirtilen agent tiplerini karşılaştırır ve grafiklerini üretir.
    Args:
        agent_types: Agent tipleri listesi
        num_games: Oynanacak oyun sayısı 
        starting_stack: Başlangıç chip miktarı
        max_round: Her oyunda oynanacak maksimum el sayısı
        small_blind: Küçük blind miktarı
    Returns:
        stats: Karşılaştırma istatistikleri içeren sözlük
    """
    print(f"Agent Karşılaştırma Benchmark'ı Başlatılıyor...")
    print(f"Agent Tipleri: {', '.join(agent_types)}")
    print(f"Oyun Sayısı: {num_games}, Başlangıç Stack: {starting_stack}, Max El: {max_round}")
    
    # İstatistikler için veri yapıları
    stats = {
        "wins": {agent_type: 0 for agent_type in agent_types},
        "final_stacks": {agent_type: [] for agent_type in agent_types},
        "avg_final_stack": {agent_type: 0 for agent_type in agent_types},
        "win_rate": {agent_type: 0 for agent_type in agent_types},
        "showdown_wins": {agent_type: 0 for agent_type in agent_types},
        "all_in_count": {agent_type: 0 for agent_type in agent_types},
        "fold_count": {agent_type: 0 for agent_type in agent_types},
        "raise_count": {agent_type: 0 for agent_type in agent_types},
        "rounds_survived": {agent_type: [] for agent_type in agent_types},
        "games_history": []
    }
    
    # Her oyun için
    for game_idx in range(num_games):
        print(f"Oyun {game_idx+1}/{num_games} oynanıyor...")
        
        # Oyun nesnesini oluştur
        game = PokerGame(
            player_names=[f"Player-{i}" for i in range(len(agent_types))],
            player_types=agent_types,
            starting_stack=starting_stack,
            max_round=max_round,
            small_blind=small_blind
        )
        
        # Oyuncuları agent'lar ile değiştir
        game.players = []
        for i, agent_type in enumerate(agent_types):
            agent = create_agent(agent_type, f"{agent_type}-{i+1}", starting_stack)
            agent.is_human = False
            agent.id = i
            # İstatistik verilerini tutacak ekstra alanlar ekle
            agent.showdown_wins = 0
            agent.all_in_count = 0
            agent.fold_count = 0
            agent.raise_count = 0
            game.players.append(agent)
        
        # Başlangıç round durumu
        current_round = 0
        eliminated_round = {agent_type: max_round for agent_type in agent_types}  # Her agent'ın elendiği round
        
        # Tüm elleri oyna
        while current_round < max_round:
            current_round += 1
            game.round = current_round
            
            # Aktif oyuncuları belirle (Stack > 0)
            active_players = [p for p in game.players if p.stack > 0]
            
            # Elenen oyuncuların elendikleri turu kaydet
            for i, player in enumerate(game.players):
                if player.stack <= 0 and eliminated_round[agent_types[i]] == max_round:
                    eliminated_round[agent_types[i]] = current_round
            
            if len(active_players) <= 1:
                break  # Yeterli aktif oyuncu yoksa oyunu bitir
                
            # Önceki eli temizle
            game.reset_round()
            
            # Oyun mekaniği (mevcut koddan)
            # ... (mevcut oyun döngüsü kodu)
            # Desteyi karıştır ve kartları dağıt
            game.deck.shuffle()
            game.deal_hole_cards()
            
            # Aktif oyuncular arasından dealer, small blind ve big blind pozisyonlarını belirle
            active_count = len(active_players)
            dealer_idx = current_round % active_count
            sb_idx = (dealer_idx + 1) % active_count
            bb_idx = (dealer_idx + 2) % active_count
            
            # Small blind ve big blind oyuncularını al
            small_blind_player = active_players[sb_idx]
            big_blind_player = active_players[bb_idx]
            
            # Small blind
            small_blind_amount = min(small_blind, small_blind_player.stack)
            game.place_bet(small_blind_player, small_blind_amount)
            
            # Big blind
            big_blind_amount = min(small_blind * 2, big_blind_player.stack)
            game.place_bet(big_blind_player, big_blind_amount)
            
            # Current bet'i büyük blind olarak ayarla
            game.current_bet = big_blind_amount
            
            # Aksiyon sayaçlarını takip et
            # Preflop turunu oynamadan önce sayaçları sıfırla
            for player in game.players:
                player.action_this_round = {"fold": 0, "call": 0, "check": 0, "raise": 0, "all_in": 0}
            
            # Preflop - Big blind'ın yanındaki oyuncudan başla
            current_betting_idx = (bb_idx + 1) % active_count
            play_betting_round(game, active_players, current_betting_idx)
            
            # İstatistik güncelleme - aksiyon sayaçları
            for player in game.players:
                i = player.id
                agent_type = agent_types[i]
                if hasattr(player, 'action_this_round'):
                    if player.action_this_round.get('fold', 0) > 0:
                        stats['fold_count'][agent_type] += 1
                    if player.action_this_round.get('raise', 0) > 0:
                        stats['raise_count'][agent_type] += 1
                    if player.stack == 0 and not player.is_folded:
                        stats['all_in_count'][agent_type] += 1
            
            # Oyun devam ediyor mu kontrol et
            if len([p for p in game.players if not p.is_folded]) <= 1:
                # Showdown - kazanan belirleme
                winner = determine_winner(game)
                if winner:
                    winner.stack += game.pot
                    stats['showdown_wins'][agent_types[winner.id]] += 1
                    game.pot = 0
                continue
            
            # Flop
            game.deal_community_cards(3)
            reset_betting_round(game)
            for player in game.players:
                player.action_this_round = {"fold": 0, "call": 0, "check": 0, "raise": 0, "all_in": 0}
            # Flop için dealer'dan sonraki ilk oyuncu bahis turunu başlatır
            start_idx = (dealer_idx + 1) % active_count
            play_betting_round(game, active_players, start_idx)
            
            # İstatistik güncelleme
            for player in game.players:
                i = player.id
                agent_type = agent_types[i]
                if hasattr(player, 'action_this_round'):
                    if player.action_this_round.get('fold', 0) > 0:
                        stats['fold_count'][agent_type] += 1
                    if player.action_this_round.get('raise', 0) > 0:
                        stats['raise_count'][agent_type] += 1
                    if player.stack == 0 and not player.is_folded:
                        stats['all_in_count'][agent_type] += 1
            
            # Oyun devam ediyor mu kontrol et
            if len([p for p in game.players if not p.is_folded]) <= 1:
                # Showdown - kazanan belirleme
                winner = determine_winner(game)
                if winner:
                    winner.stack += game.pot
                    stats['showdown_wins'][agent_types[winner.id]] += 1
                    game.pot = 0
                continue
            
            # Turn
            game.deal_community_cards(1)
            reset_betting_round(game)
            for player in game.players:
                player.action_this_round = {"fold": 0, "call": 0, "check": 0, "raise": 0, "all_in": 0}
            # Turn için dealer'dan sonraki ilk oyuncu bahis turunu başlatır
            start_idx = (dealer_idx + 1) % active_count
            play_betting_round(game, active_players, start_idx)
            
            # İstatistik güncelleme
            for player in game.players:
                i = player.id
                agent_type = agent_types[i]
                if hasattr(player, 'action_this_round'):
                    if player.action_this_round.get('fold', 0) > 0:
                        stats['fold_count'][agent_type] += 1
                    if player.action_this_round.get('raise', 0) > 0:
                        stats['raise_count'][agent_type] += 1
                    if player.stack == 0 and not player.is_folded:
                        stats['all_in_count'][agent_type] += 1
            
            # Oyun devam ediyor mu kontrol et
            if len([p for p in game.players if not p.is_folded]) <= 1:
                # Showdown - kazanan belirleme
                winner = determine_winner(game)
                if winner:
                    winner.stack += game.pot
                    stats['showdown_wins'][agent_types[winner.id]] += 1
                    game.pot = 0
                continue
            
            # River
            game.deal_community_cards(1)
            reset_betting_round(game)
            for player in game.players:
                player.action_this_round = {"fold": 0, "call": 0, "check": 0, "raise": 0, "all_in": 0}
            # River için dealer'dan sonraki ilk oyuncu bahis turunu başlatır
            start_idx = (dealer_idx + 1) % active_count
            play_betting_round(game, active_players, start_idx)
            
            # İstatistik güncelleme
            for player in game.players:
                i = player.id
                agent_type = agent_types[i]
                if hasattr(player, 'action_this_round'):
                    if player.action_this_round.get('fold', 0) > 0:
                        stats['fold_count'][agent_type] += 1
                    if player.action_this_round.get('raise', 0) > 0:
                        stats['raise_count'][agent_type] += 1
                    if player.stack == 0 and not player.is_folded:
                        stats['all_in_count'][agent_type] += 1
            
            # Showdown
            process_showdown(game)
        
        # Oyun sonuçlarını kaydet
        game_results = {
            "game_idx": game_idx,
            "final_stacks": {},
            "winner": None,
            "rounds_played": current_round
        }
        
        # En çok stack'e sahip oyuncuyu bul
        max_stack = -1
        winner_idx = -1
        
        for i, player in enumerate(game.players):
            agent_type = agent_types[i]
            
            # Final stack'i kaydet
            stats["final_stacks"][agent_type].append(player.stack)
            game_results["final_stacks"][agent_type] = player.stack
            
            # Rounds survived - eğer oyuncu elendiyse
            if player.stack <= 0:
                stats["rounds_survived"][agent_type].append(eliminated_round[agent_type])
            else:
                stats["rounds_survived"][agent_type].append(max_round)
            
            # Kazanan kontrolü
            if player.stack > max_stack:
                max_stack = player.stack
                winner_idx = i
        
        # Kazananı kaydet
        if winner_idx >= 0:
            winner_type = agent_types[winner_idx]
            stats["wins"][winner_type] += 1
            game_results["winner"] = winner_type
        
        # Oyun tarihçesini kaydet
        stats["games_history"].append(game_results)
        
    # İstatistikleri hesapla
    for agent_type in agent_types:
        stats["avg_final_stack"][agent_type] = np.mean(stats["final_stacks"][agent_type])
        stats["win_rate"][agent_type] = stats["wins"][agent_type] / num_games
    
    # Sonuçları yazdır
    print("\nKarşılaştırma Sonuçları:")
    print("-" * 60)
    for agent_type in agent_types:
        print(f"{agent_type}:")
        print(f"  Kazanma Oranı: {stats['win_rate'][agent_type]:.2f} ({stats['wins'][agent_type]}/{num_games})")
        print(f"  Ortalama Final Stack: {stats['avg_final_stack'][agent_type]:.2f}")
        print(f"  Showdown Kazanma: {stats['showdown_wins'][agent_type]}")
        print(f"  All-in Sayısı: {stats['all_in_count'][agent_type]}")
        print(f"  Fold Sayısı: {stats['fold_count'][agent_type]}")
        print(f"  Raise Sayısı: {stats['raise_count'][agent_type]}")
        if stats["rounds_survived"][agent_type]:
            print(f"  Ortalama Hayatta Kalınan Tur: {np.mean(stats['rounds_survived'][agent_type]):.2f}")
        print("-" * 30)
    
    # Grafikleri oluştur
    plot_comparison_charts(stats, agent_types, num_games)
    
    return stats

def plot_comparison_charts(stats, agent_types, num_games):
    """
    Ajan karşılaştırma grafikleri oluşturur ve kaydeder
    """
    colors = ["#2E86C1", "#E67E22", "#27AE60", "#8E44AD"]  # Karşılaştırma grafikleri için renkler
    
    # 1. Kazanma Oranları Grafiği
    plt.figure(figsize=(10, 6))
    win_rates = [stats["win_rate"][agent] for agent in agent_types]
    bars = plt.bar(agent_types, win_rates, color=colors)
    plt.title("Agent Kazanma Oranları", fontsize=14)
    plt.ylabel("Kazanma Oranı")
    plt.ylim(0, 1)
    
    # Barların üzerinde değerleri göster
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.01,
                f'{height:.2f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig("kazanma_oranlari.png", dpi=300)
    
    # 2. Ortalama Final Stack Grafiği
    plt.figure(figsize=(10, 6))
    avg_stacks = [stats["avg_final_stack"][agent] for agent in agent_types]
    bars = plt.bar(agent_types, avg_stacks, color=colors)
    plt.title("Ortalama Final Stack", fontsize=14)
    plt.ylabel("Chip Miktarı")
    
    # Barların üzerinde değerleri göster
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 1,
                f'{height:.0f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig("ortalama_stack.png", dpi=300)
    
    # 3. Aksiyon İstatistikleri (All-in, Fold, Raise, Showdown)
    plt.figure(figsize=(12, 7))
    
    action_data = {
        'All-in': [stats["all_in_count"][agent] for agent in agent_types],
        'Fold': [stats["fold_count"][agent] for agent in agent_types],
        'Raise': [stats["raise_count"][agent] for agent in agent_types],
        'Showdown Wins': [stats["showdown_wins"][agent] for agent in agent_types]
    }
    
    df = pd.DataFrame(action_data, index=agent_types)
    df.plot(kind='bar', figsize=(12, 7))
    plt.title("Aksiyon İstatistikleri", fontsize=14)
    plt.ylabel("Sayı")
    plt.xlabel("Agent Tipi")
    plt.xticks(rotation=0)
    plt.legend(title="Aksiyon Tipi")
    plt.tight_layout()
    plt.savefig("aksiyon_istatistikleri.png", dpi=300)
    
    # 4. Hayatta Kalınan Ortalama Tur
    plt.figure(figsize=(10, 6))
    avg_rounds = [np.mean(stats["rounds_survived"][agent]) for agent in agent_types]
    bars = plt.bar(agent_types, avg_rounds, color=colors)
    plt.title("Ortalama Hayatta Kalınan Tur", fontsize=14)
    plt.ylabel("Tur Sayısı")
    
    # Barların üzerinde değerleri göster
    for bar in bars:
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                f'{height:.1f}', ha='center', va='bottom')
    
    plt.tight_layout()
    plt.savefig("hayatta_kalma_turu.png", dpi=300)
    
    # 5. Final Stack Dağılımı (Box Plot)
    plt.figure(figsize=(10, 6))
    box_data = [stats["final_stacks"][agent] for agent in agent_types]
    plt.boxplot(box_data, labels=agent_types)
    plt.title("Final Stack Dağılımı", fontsize=14)
    plt.ylabel("Chip Miktarı")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.tight_layout()
    plt.savefig("stack_dagilimi.png", dpi=300)
    
    # Tüm grafikleri tek bir şekilde de göster
    plt.figure(figsize=(16, 10))
    
    # 2x3 grid layout
    plt.subplot(2, 3, 1)
    plt.bar(agent_types, win_rates, color=colors)
    plt.title("Kazanma Oranları")
    plt.ylabel("Oran")
    
    plt.subplot(2, 3, 2)
    plt.bar(agent_types, avg_stacks, color=colors)
    plt.title("Ortalama Final Stack")
    plt.ylabel("Chip")
    
    plt.subplot(2, 3, 3)
    plt.bar(agent_types, avg_rounds, color=colors)
    plt.title("Hayatta Kalınan Tur")
    plt.ylabel("Tur")
    
    plt.subplot(2, 3, 4)
    bar_width = 0.2
    index = np.arange(len(agent_types))
    
    plt.bar(index, action_data['All-in'], bar_width, label='All-in', color=colors[0])
    plt.bar(index + bar_width, action_data['Fold'], bar_width, label='Fold', color=colors[1])
    plt.bar(index + 2*bar_width, action_data['Raise'], bar_width, label='Raise', color=colors[2])
    plt.bar(index + 3*bar_width, action_data['Showdown Wins'], bar_width, label='Showdown', color=colors[3])
    
    plt.xlabel('Agent')
    plt.ylabel('Sayı')
    plt.title('Aksiyon İstatistikleri')
    plt.xticks(index + 1.5*bar_width, agent_types)
    plt.legend()
    
    plt.subplot(2, 3, 5)
    plt.boxplot(box_data, labels=agent_types)
    plt.title("Stack Dağılımı (Box Plot)")
    plt.ylabel("Chip")
    
    plt.tight_layout()
    plt.savefig("tum_istatistikler.png", dpi=300)
    
    print("Grafikler kaydedildi: kazanma_oranlari.png, ortalama_stack.png, aksiyon_istatistikleri.png, hayatta_kalma_turu.png, stack_dagilimi.png, tum_istatistikler.png")

def main():
    """Ana program - Komut satırı argümanlarını işler ve uygun modu başlatır"""
    parser = argparse.ArgumentParser(description="Poker AI Karşılaştırma Aracı")
    parser.add_argument("--mode", choices=["ui", "ai_compare", "benchmark"], default="ui",
                      help="Çalıştırma modu: ui (kullanıcı arayüzü), ai_compare (AI performans karşılaştırması) veya benchmark (grafik üreten detaylı karşılaştırma)")
    
    # AI Karşılaştırma ve Benchmark modu için ek parametreler
    parser.add_argument("--agents", nargs="+", default=["basic_heuristic", "aggressive_heuristic", "mcts", "expectiminimax"],
                      help="Karşılaştırılacak agent tipleri (boşlukla ayrılmış)")
    parser.add_argument("--games", type=int, default=100, 
                      help="Oynanacak oyun sayısı")
    parser.add_argument("--max_round", type=int, default=10,
                      help="Her oyunda oynanacak maksimum el sayısı")
    parser.add_argument("--stack", type=int, default=1000,
                      help="Başlangıç chip miktarı")
    parser.add_argument("--small_blind", type=int, default=10,
                      help="Küçük blind miktarı")
    parser.add_argument("--output", default="",
                      help="Sonuçların yazılacağı dosya (belirtilmezse tarih/saat damgalı bir ad oluşturulur)")
    
    args = parser.parse_args()
    
    if args.mode == "ui":
        # UI modunu başlat
        start_ui()
    elif args.mode == "benchmark":
        # Benchmark modu (grafikli)
        stats = benchmark_agents(
            agent_types=args.agents,
            num_games=args.games,
            starting_stack=args.stack,
            max_round=args.max_round,
            small_blind=args.small_blind
        )
        
        # İstatistikleri JSON olarak kaydet
        if not args.output:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"benchmark_results_{timestamp}.json"
        else:
            output_file = args.output
            
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, indent=4, ensure_ascii=False)
        
        print(f"Ayrıntılı sonuçlar '{output_file}' dosyasına kaydedildi.")
    else:
        # AI performans karşılaştırma modunu başlat
        if not args.output:
            # Çıktı dosyası belirtilmemişse, tarih ve saat damgalı bir ad oluştur
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_file = f"ai_comparison_{timestamp}.json"
        else:
            output_file = args.output
        
        run_ai_comparison(
            agent_types=args.agents,
            num_games=args.games,
            starting_stack=args.stack,
            max_round=args.max_round,
            small_blind=args.small_blind,
            output_file=output_file
        )

def el_gucu_hesapla(hole_cards, community_cards):
    """Treys kütüphanesini kullanarak el gücünü hesapla"""
    from treys import Card as TreysCard, Evaluator
    
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
    evaluator = Evaluator()
    score = evaluator.evaluate(treys_community_cards, treys_hole_cards)
    return score

if __name__ == "__main__":
    main() 