import tkinter as tk
from tkinter import ttk, messagebox
import os
import sys
from treys import Card as TreysCard, Evaluator
import random

from poker import PokerGame, Player
from heuristic_agent import BasicHeuristicAgent, AggressiveHeuristicAgent
from mcts_agent import MCTSAgent
from expectiminimax_agent import ExpectiminimaxAgent

def el_gucu_hesapla(hole_cards, community_cards):
    # Treys evaluator kullanarak el gücünü hesapla
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

class PokerUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Poker Ajanları")
        
        # Tam ekran modu
        self.root.attributes('-fullscreen', True)
        
        # Stillerini ayarla
        self.configure_styles()
        
        # Varsayılan arkaplan rengini yeşil yap
        self.root.configure(bg="#0a6e0a")  # Koyu yeşil
        
        self.game = None
        self.player_frames = {}
        self.community_card_labels = []
        self.card_images = {}
        self.settings = {}
        self.log_text = None
        
        # Çıkış tuşu (ESC)
        self.root.bind("<Escape>", lambda event: self.root.attributes("-fullscreen", False))
        
        # Kart resimlerini yükle
        self.load_card_images()
    
    def configure_styles(self):
        """Tüm stilleri yapılandır"""
        style = ttk.Style()
        
        # Arka plan renkleri
        bg_color = "#0a6e0a"  # Koyu yeşil
        fg_color = "white"
        button_bg = "#1e401e"
        button_active_bg = "#2d602d"
        
        # Tttk temalarını ayarla
        style.theme_use("alt")  # Alt tema daha fazla özelleştirme seçeneği sunar
        
        # Tüm stillerin varsayılan arka planını ayarla
        style.configure(".", background=bg_color, foreground=fg_color)
        
        # Temel widget stilleri
        style.configure("TFrame", background=bg_color)
        style.configure("TLabel", background=bg_color, foreground=fg_color)
        style.configure("TLabelframe", background=bg_color, foreground=fg_color, bordercolor=bg_color)
        style.configure("TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Arial", 12, "bold"))
        style.configure("TButton", background=button_bg, foreground=fg_color, font=("Arial", 11))
        style.configure("TEntry", fieldbackground="#ffffff", foreground="#000000", background=bg_color)
        style.configure("TSpinbox", fieldbackground="#ffffff", foreground="#000000", arrowcolor=fg_color, background=bg_color)
        style.configure("TCombobox", fieldbackground="#ffffff", foreground="#000000", background=bg_color)
        style.configure("TScrollbar", background=bg_color, troughcolor=bg_color, arrowcolor=fg_color)
        style.configure("TNotebook", background=bg_color)
        style.configure("TNotebook.Tab", background=bg_color, foreground=fg_color)
        
        # Çerçeve ve kenarlıkları yeşil yapma
        style.map("TLabelframe", background=[("active", bg_color)])
        style.map("TLabel", background=[("active", bg_color)])
        
        # Özel yeşil stiller
        style.configure("Green.TFrame", background=bg_color)
        style.configure("Green.TLabel", background=bg_color, foreground=fg_color)
        style.configure("Green.TLabelframe", background=bg_color, foreground=fg_color, bordercolor=bg_color)
        style.configure("Green.TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Arial", 12, "bold"))
        
        # Aktif oyuncu stili (sarı çerçeve)
        style.configure("ActivePlayer.TLabelframe", background=bg_color, foreground=fg_color, bordercolor="yellow", borderwidth=2)
        style.configure("ActivePlayer.TLabelframe.Label", background=bg_color, foreground=fg_color, font=("Arial", 12, "bold"))
        
        # Buton stilleri
        style.map("TButton",
                 background=[('active', button_active_bg)],
                 foreground=[('active', fg_color)])
        style.map("Green.TButton",
                 background=[('active', button_active_bg)],
                 foreground=[('active', fg_color)])
                 
        # Canvas stilleri (kartlar için)
        style.configure("Card.TFrame", background=bg_color, borderwidth=0, relief="flat")
    
    def load_card_images(self):
        # Kart resimlerini images klasöründen yükle
        images_dir = "images"
        if not os.path.exists(images_dir):
            print(f"Hata: {images_dir} klasörü bulunamadı!")
            # Varsayılan kart resmi oluştur
            self.create_default_card_images()
            return
            
        # Joker kartını özel olarak yükle (siyah kart arkası olarak da kullanacağız)
        joker_image_path = os.path.join(images_dir, "black_joker.png")
        if os.path.exists(joker_image_path):
            joker_img = tk.PhotoImage(file=joker_image_path)
            joker_img = joker_img.subsample(4, 4)  # Resmi küçült
            self.card_images["black_joker"] = joker_img
            # Joker kartını back olarak da kullan
            self.card_images["back"] = joker_img
        else:
            # Varsayılan joker kartı oluştur
            self.create_default_joker_image()
            # Joker kartını back olarak da kullan
            self.card_images["back"] = self.card_images["black_joker"]
            
        # Diğer kartları yükle
        for filename in os.listdir(images_dir):
            if filename.endswith(".png") and filename != "back.png" and filename != "black_joker.png":
                # Dosya adından kart bilgisini al (örn: ace_of_spades.png -> ace_of_spades)
                card_name = os.path.splitext(filename)[0]
                image_path = os.path.join(images_dir, filename)
                
                # Kart resmini yükle ve boyutlandır
                img = tk.PhotoImage(file=image_path)
                img = img.subsample(4, 4)  # Resmi küçült
                self.card_images[card_name] = img
    
    def create_default_card_images(self):
        # Resim yoksa varsayılan kartlar oluştur
        self.create_default_back_image()
        self.create_default_joker_image()
    
    def create_default_back_image(self):
        # Varsayılan kart arkası oluştur (kırmızı dikdörtgen ve daha estetik)
        img = tk.PhotoImage(width=90, height=130)
        
        # Kart arka planı
        for y in range(130):
            for x in range(90):
                # Kenarlarda biraz daha koyu, ortada daha açık kırmızı
                if x < 5 or x > 84 or y < 5 or y > 124:
                    img.put("#990000", (x, y))  # Koyu kırmızı kenar
                else:
                    img.put("#cc0000", (x, y))  # Kırmızı arka plan
        
        # Kart deseni ekle (basit bir desen)
        for y in range(10, 120, 10):
            for x in range(10, 80, 10):
                # Diagonal pattern
                for dy in range(5):
                    for dx in range(5):
                        if dx == dy or dx == 4-dy:
                            img.put("#ff5555", (x+dx, y+dy))  # Açık kırmızı desenler
                            
        # Kart sınırı (beyaz çerçeve)
        for y in range(130):
            for x in range(90):
                if x == 0 or x == 89 or y == 0 or y == 129:
                    img.put("#ffffff", (x, y))
                    
        self.card_images["back"] = img
    
    def create_default_joker_image(self):
        # Varsayılan joker kartı oluştur (siyah zeminde yazı)
        img = tk.PhotoImage(width=90, height=130)
        
        # Siyah arka plan
        for y in range(130):
            for x in range(90):
                if x < 2 or x > 87 or y < 2 or y > 127:  # Beyaz kenar bırak
                    img.put("#ffffff", (x, y))
                else:
                    img.put("#000000", (x, y))
                
        # "JOKER" yazısını ekleme
        joker_text = "JOKER"
        for i, char in enumerate(joker_text):
            start_y = 40 + (i * 10)
            for y in range(start_y, start_y + 8):
                for x in range(30, 60):
                    if (y - start_y) % 2 == 0 and (x - 30) % 2 == 0:
                        img.put("#ff0000", (x, y))  # Kırmızı renkli pixeller ile "JOKER" yazısı
                    
        self.card_images["black_joker"] = img
    
    def setup_screen(self):
        # Ayar ekranını oluştur
        settings_frame = ttk.Frame(self.root, padding="10", style="Green.TFrame")
        
        # Tüm pencerenin arka planını ayarla
        self.root.config(bg="#0a6e0a")
        
        # Merkezi konumlandırma için
        self.root.update()
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Ayar frame'in genişliği ve yüksekliği
        frame_width = 600
        frame_height = 700
        
        # Merkez koordinatları hesapla
        x = (window_width - frame_width) // 2
        y = (window_height - frame_height) // 2
        
        # Frame'i yerleştir
        settings_frame.place(x=x, y=y, width=frame_width, height=frame_height)
        
        # Başlık
        ttk.Label(settings_frame, text="Poker Ayarları", font=("Arial", 22, "bold"), 
                 style="Green.TLabel").grid(row=0, column=0, columnspan=2, pady=20)
        
        # MaxRound
        ttk.Label(settings_frame, text="Maksimum El Sayısı:", font=("Arial", 12), 
                 style="Green.TLabel").grid(row=1, column=0, sticky="w", pady=5)
        max_round_var = tk.IntVar(value=10)
        ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=max_round_var, width=10, 
                   font=("Arial", 12)).grid(row=1, column=1, sticky="w", pady=5)
        
        # Initial Stack
        ttk.Label(settings_frame, text="Başlangıç Chip Miktarı:", font=("Arial", 12), 
                 style="Green.TLabel").grid(row=2, column=0, sticky="w", pady=5)
        initial_stack_var = tk.IntVar(value=1000)
        ttk.Spinbox(settings_frame, from_=100, to=10000, textvariable=initial_stack_var, width=10, 
                   font=("Arial", 12)).grid(row=2, column=1, sticky="w", pady=5)
        
        # Small Blind
        ttk.Label(settings_frame, text="Küçük Blind Miktarı:", font=("Arial", 12), 
                 style="Green.TLabel").grid(row=3, column=0, sticky="w", pady=5)
        small_blind_var = tk.IntVar(value=10)
        ttk.Spinbox(settings_frame, from_=1, to=100, textvariable=small_blind_var, width=10, 
                   font=("Arial", 12)).grid(row=3, column=1, sticky="w", pady=5)
        
        # Number of AI Players
        ttk.Label(settings_frame, text="Yapay Zeka Oyuncu Sayısı:", font=("Arial", 12), 
                 style="Green.TLabel").grid(row=4, column=0, sticky="w", pady=5)
        ai_count_var = tk.IntVar(value=2)  # Varsayılan değeri 2 yaptım
        ai_count_spinbox = ttk.Spinbox(settings_frame, from_=1, to=3, textvariable=ai_count_var, width=10, 
                                      font=("Arial", 12))
        ai_count_spinbox.grid(row=4, column=1, sticky="w", pady=5)
        
        # Player Name
        ttk.Label(settings_frame, text="Oyuncu Adı:", font=("Arial", 12), 
                 style="Green.TLabel").grid(row=5, column=0, sticky="w", pady=5)
        player_name_var = tk.StringVar(value="İnsan Oyuncu")
        ttk.Entry(settings_frame, textvariable=player_name_var, width=20, 
                 font=("Arial", 12)).grid(row=5, column=1, sticky="w", pady=5)
        
        # AI Player Types Frame
        ai_frame = ttk.LabelFrame(settings_frame, text="Yapay Zeka Oyuncu Tipleri", padding="10", style="Green.TLabelframe")
        ai_frame.grid(row=6, column=0, columnspan=2, sticky="ew", pady=10)
        
        # AI Player Types (dinamik olarak oluştur)
        ai_types = ["Basic Heuristic", "Aggressive Heuristic", "MCTS", "Expectiminimax"]
        ai_type_vars = []
        ai_rows = []  # AI satırlarını takip et
        
        max_ai_players = 5
        for i in range(max_ai_players):
            ai_row = ttk.Frame(ai_frame, style="Green.TFrame")
            ai_row.grid(row=i, column=0, sticky="ew", pady=5)
            ai_rows.append(ai_row)
            
            ttk.Label(ai_row, text=f"AI {i+1} Tipi:", font=("Arial", 11), style="Green.TLabel").grid(row=0, column=0, sticky="w", pady=5)
            ai_type_var = tk.StringVar(value=ai_types[i % len(ai_types)])
            ai_type_combo = ttk.Combobox(ai_row, values=ai_types, textvariable=ai_type_var, state="readonly", width=15, font=("Arial", 11))
            ai_type_combo.grid(row=0, column=1, sticky="w", pady=5)
            ai_type_vars.append(ai_type_var)
            
            ttk.Label(ai_row, text=f"AI {i+1} Adı:", font=("Arial", 11), style="Green.TLabel").grid(row=0, column=2, sticky="w", padx=10, pady=5)
            ai_name_var = tk.StringVar(value=f"AI {i+1}")
            ttk.Entry(ai_row, textvariable=ai_name_var, width=15, font=("Arial", 11)).grid(row=0, column=3, sticky="w", pady=5)
            ai_type_vars.append(ai_name_var)
            
            # Başlangıçta sadece seçilen AI sayısı kadar göster
            if i >= ai_count_var.get():
                ai_row.grid_remove()
        
        # AI oyuncu sayısı değiştiğinde dinamik güncelleme
        def update_ai_rows(*args):
            count = ai_count_var.get()
            for i, row in enumerate(ai_rows):
                if i < count:
                    row.grid()
                else:
                    row.grid_remove()
            
            # Ayar frame'in yüksekliğini güncelle
            frame_height = 500 + count * 40
            settings_frame.config(height=frame_height)
            y = (window_height - frame_height) // 2
            settings_frame.place(y=y)
        
        ai_count_var.trace_add("write", update_ai_rows)
        
        # Başlat butonu
        def start_game():
            # Ayarları kaydet
            ai_count = ai_count_var.get()
            self.settings = {
                "max_round": max_round_var.get(),
                "starting_stack": initial_stack_var.get(),
                "small_blind": small_blind_var.get(),
                "player_name": player_name_var.get(),
                "ai_count": ai_count,
                "ai_types": [ai_type_vars[i*2].get() for i in range(ai_count)],
                "ai_names": [ai_type_vars[i*2+1].get() for i in range(ai_count)]
            }
            
            # Ayar ekranını kaldır
            settings_frame.destroy()
            
            # Oyun ekranını oluştur
            self.create_game()
            self.game_screen()
        
        # Başlat butonu oluştur ve altına yerleştir
        ttk.Button(settings_frame, text="Oyunu Başlat", command=start_game, 
                  style="Green.TButton", padding=10).grid(row=7, column=0, columnspan=2, pady=20)
        
        # Başlangıçta AI satırlarını güncelle
        update_ai_rows()
    
    def create_game(self):
        # PokerGame örneği oluştur
        player_names = [self.settings["player_name"]] + self.settings["ai_names"]
        player_types = ["human"] + self.settings["ai_types"]
        
        # Oyun nesnesini oluştur
        self.game = PokerGame(player_names, player_types, self.settings["starting_stack"], 
                             self.settings["max_round"], self.settings["small_blind"])
        
        # Oyuncuları oluştur ve oyuna ekle
        self.game.players = []
        
        # İnsan oyuncu
        human_player = Player(self.settings["player_name"], self.settings["starting_stack"])
        human_player.is_human = True
        self.game.players.append(human_player)
        
        # AI oyuncular
        for i in range(self.settings["ai_count"]):
            ai_name = self.settings["ai_names"][i]
            ai_type = self.settings["ai_types"][i]
            
            if ai_type == "Basic Heuristic":
                ai_player = BasicHeuristicAgent(ai_name, self.settings["starting_stack"])
            elif ai_type == "Aggressive Heuristic":
                ai_player = AggressiveHeuristicAgent(ai_name, self.settings["starting_stack"])
            elif ai_type == "MCTS":
                ai_player = MCTSAgent(ai_name, self.settings["starting_stack"])
            elif ai_type == "Expectiminimax":
                ai_player = ExpectiminimaxAgent(ai_name, self.settings["starting_stack"])
            else:
                ai_player = Player(ai_name, self.settings["starting_stack"])
                
            ai_player.is_human = False
            self.game.players.append(ai_player)
            
        # Oyunu başlat
        self.game.reset_round()
        
        # Sadece hazırlık aşamasında, next_round() metodu kartları dağıtacak
    
    def game_screen(self):
        # Tüm pencere bileşenlerini yeşil yap
        self.root.configure(bg="#0a6e0a")
        
        # Ana frame'i transparan yap (yeşil arka planı görelim)
        game_frame = ttk.Frame(self.root, padding="10", style="Green.TFrame")
        game_frame.pack(fill="both", expand=True)
        
        # Üst bilgi çubuğu
        info_frame = ttk.Frame(game_frame, padding="5", style="Green.TFrame")
        info_frame.pack(fill="x", pady=5)
        
        self.pot_label = ttk.Label(info_frame, text=f"Pot: {self.game.pot}", font=("Arial", 14, "bold"), style="Green.TLabel")
        self.pot_label.pack(side="left", padx=10)
        
        self.round_label = ttk.Label(info_frame, text=f"El: {self.game.round}/{self.settings['max_round']}", font=("Arial", 14, "bold"), style="Green.TLabel")
        self.round_label.pack(side="right", padx=10)
        
        # Ana içerik bölümü - açık yeşil arka plan
        content_frame = ttk.Frame(game_frame, style="Green.TFrame")
        content_frame.pack(fill="both", expand=True, pady=5)
        
        # Oyun bölgesi (sol taraf)
        game_area = ttk.Frame(content_frame, style="Green.TFrame")
        game_area.pack(side="left", fill="both", expand=True)
        
        # Log bölgesi (sağ taraf)
        log_frame = ttk.LabelFrame(content_frame, text="Oyun Logları", style="Green.TLabelframe", padding=10)
        log_frame.pack(side="right", fill="both", expand=False, padx=10, pady=5)
        
        # Log ekranını siyah arka plan beyaz yazı şeklinde ayarla
        self.log_text = tk.Text(log_frame, width=40, height=30, bg="#000000", fg="#ffffff", font=("Courier", 10))
        self.log_text.pack(fill="both", expand=True)
        
        # Kaydırma çubuğu
        scrollbar = ttk.Scrollbar(log_frame, command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.config(yscrollcommand=scrollbar.set)
        
        # Log'a başlangıç mesajı
        self.add_log("Oyun başladı!")
        self.add_log(f"Oyuncu: {self.settings['player_name']}")
        self.add_log(f"AI Oyuncular: {', '.join(self.settings['ai_names'])}")
        self.add_log(f"Başlangıç Stack: {self.settings['starting_stack']}")
        self.add_log(f"Küçük Blind: {self.settings['small_blind']}")
        
        # AI oyuncular (üst kısım)
        ai_players_frame = ttk.Frame(game_area, style="Green.TFrame")
        ai_players_frame.pack(fill="x", pady=5)
        
        # AI oyuncuları grid yerleşim ile dağıt
        cols = min(3, self.settings["ai_count"])  # Daha az sütun kullanarak daha büyük göster
        rows = (self.settings["ai_count"] + cols - 1) // cols  # Tavana yuvarla
        
        self.player_frames = {}
        
        # AI oyuncuları ekle
        for i in range(1, len(self.game.players)):
            ai_frame = ttk.LabelFrame(ai_players_frame, text=self.game.players[i].name, style="Green.TLabelframe", padding=5)
            
            # Oyuncuların pozisyonunu hesapla
            row_idx = (i - 1) // cols
            col_idx = (i - 1) % cols
            
            # Frame'ler arası mesafeyi artır ve üst üste binmeyi engelle
            ai_frame.grid(row=row_idx, column=col_idx, padx=20, pady=15, sticky="nsew")  # sticky="nsew" eklendi
            
            # Grid hücrelerinin minimum boyutunu ayarla
            ai_players_frame.grid_columnconfigure(col_idx, minsize=200, weight=1)  # weight=1 eklendi
            ai_players_frame.grid_rowconfigure(row_idx, minsize=150, weight=1)  # weight=1 eklendi
            
            # Frame'i minimum 180x100 boyutunda yap
            ai_frame.columnconfigure(0, minsize=180)
            ai_frame.rowconfigure(0, minsize=100)
            
            self.player_frames[i] = self.create_player_ui(ai_frame, i)
        
        # Masa (community kartlar) - daha küçük ve çerçeveli
        table_frame = ttk.LabelFrame(game_area, text="Masa", style="Green.TLabelframe", padding="5")  # padding'i küçülttüm
        table_frame.pack(fill="x", expand=True, pady=5)  # pady'yi küçülttüm
        
        # Masayı daha poker masası gibi göstermek için oval bir yeşil zemin
        community_frame = ttk.Frame(table_frame, style="Green.TFrame", height=80)  # height'i küçülttüm
        community_frame.pack(pady=5, fill="x")  # pady'yi küçülttüm
        
        # Community kartlar - daha sıkışık yerleşim
        self.community_card_labels = []
        for i in range(5):
            card_label = ttk.Label(community_frame, image=self.card_images.get("black_joker"), style="Green.TLabel")
            card_label.pack(side="left", padx=3, expand=True)  # padx'i küçülttüm
            self.community_card_labels.append(card_label)
        
        # İnsan oyuncu (altta) - çerçeveli
        human_frame = ttk.LabelFrame(game_area, text=self.game.players[0].name, style="Green.TLabelframe", padding="3")
        human_frame.pack(fill="x", pady=3, ipady=3)  # ipady'yi küçülttüm
        human_frame.configure(borderwidth=1, relief='solid')  # Çerçeveyi ekle
        self.player_frames[0] = self.create_player_ui(human_frame, 0, True)  # İnsan oyuncu için özel
        
        # Aksiyon butonları (sadece insan oyuncu için)
        action_frame = tk.Frame(game_area, bg="#0a6e0a", padx=3, pady=3)  # padx ve pady'yi küçülttüm
        action_frame.pack(fill="x", pady=3)  # pady'yi küçülttüm
        
        # Button stillerini ayarla - daha küçük butonlar
        self.button_style = {
            "font": ("Arial", 12, "bold"),  # font size küçülttüm
            "bg": "#ac1f1f",  # Kırmızı
            "fg": "white", 
            "activebackground": "#d43030",  # Açık kırmızı (hover)
            "activeforeground": "white", 
            "relief": "raised", 
            "borderwidth": 2,  # borderwidth küçülttüm
            "padx": 10,  # padx küçülttüm
            "pady": 5,  # pady küçülttüm
            "width": 8,  # width küçülttüm
            "height": 1
        }
        
        # Disabled button stilini de tanımla
        self.disabled_button_style = {
            "font": ("Arial", 12, "bold"),  # font size küçülttüm
            "bg": "#6e1f1f",  # Daha koyu kırmızı
            "fg": "white", 
            "disabledforeground": "gray80",  # Disabled yazı rengi
            "relief": "raised", 
            "borderwidth": 2,  # borderwidth küçülttüm
            "padx": 10,  # padx küçülttüm
            "pady": 5,  # pady küçülttüm
            "width": 8,  # width küçülttüm
            "height": 1
        }
        
        # Butonları ortalı göster için frame
        button_frame = tk.Frame(action_frame, bg="#0a6e0a")
        button_frame.pack(side="top", fill="x", pady=1)  # pady'yi küçülttüm
        
        # Butonların hizalanması için sol spacer
        left_spacer = tk.Frame(button_frame, bg="#0a6e0a", width=5)  # width'i küçülttüm
        left_spacer.pack(side="left", padx=1)  # padx'i küçülttüm
        
        # Butonları doğrudan oluştur (config yerine params olarak gönder)
        fold_btn = tk.Button(button_frame, text="Fold", command=self.fold_action,
                             font=self.button_style["font"],
                             bg=self.button_style["bg"],
                             fg=self.button_style["fg"],
                             activebackground=self.button_style["activebackground"],
                             activeforeground=self.button_style["activeforeground"],
                             relief=self.button_style["relief"],
                             borderwidth=self.button_style["borderwidth"],
                             padx=self.button_style["padx"],
                             pady=self.button_style["pady"],
                             width=self.button_style["width"],
                             height=self.button_style["height"])
        fold_btn.pack(side="left", padx=15)
        self.fold_btn = fold_btn
        
        check_btn = tk.Button(button_frame, text="Check", command=self.call_action,
                              font=self.button_style["font"],
                              bg=self.button_style["bg"],
                              fg=self.button_style["fg"],
                              activebackground=self.button_style["activebackground"],
                              activeforeground=self.button_style["activeforeground"],
                              relief=self.button_style["relief"],
                              borderwidth=self.button_style["borderwidth"],
                              padx=self.button_style["padx"],
                              pady=self.button_style["pady"],
                              width=self.button_style["width"],
                              height=self.button_style["height"])
        check_btn.pack(side="left", padx=15)
        self.check_btn = check_btn
        
        call_btn = tk.Button(button_frame, text="Call", command=self.call_action,
                             font=self.button_style["font"],
                             bg=self.button_style["bg"],
                             fg=self.button_style["fg"],
                             activebackground=self.button_style["activebackground"],
                             activeforeground=self.button_style["activeforeground"],
                             relief=self.button_style["relief"],
                             borderwidth=self.button_style["borderwidth"],
                             padx=self.button_style["padx"],
                             pady=self.button_style["pady"],
                             width=self.button_style["width"],
                             height=self.button_style["height"])
        call_btn.pack(side="left", padx=15)
        self.call_btn = call_btn
        
        # Min raise bilgisi
        min_raise_label = tk.Label(button_frame, text="Min: 0", font=("Arial", 12), bg="#0a6e0a", fg="white")
        min_raise_label.pack(side="left", padx=5)
        self.min_raise_label = min_raise_label
        
        # Raise Entry (butonlarla aynı satırda)
        self.raise_var = tk.IntVar(value=self.game.small_blind)
        raise_entry = tk.Spinbox(button_frame, from_=1, to=1000, 
                              textvariable=self.raise_var, width=8, 
                              font=("Arial", 14), bg="white", fg="black")
        raise_entry.pack(side="left", padx=5)
        self.raise_entry = raise_entry
        
        # Raise butonu (butonlarla aynı satırda)
        raise_btn = tk.Button(button_frame, text="Raise", command=self.raise_action,
                              font=self.button_style["font"],
                              bg=self.button_style["bg"],
                              fg=self.button_style["fg"],
                              activebackground=self.button_style["activebackground"],
                              activeforeground=self.button_style["activeforeground"],
                              relief=self.button_style["relief"],
                              borderwidth=self.button_style["borderwidth"],
                              padx=self.button_style["padx"],
                              pady=self.button_style["pady"],
                              width=self.button_style["width"],
                              height=self.button_style["height"])
        raise_btn.pack(side="left", padx=15)
        self.raise_btn = raise_btn
        
        # Sağa hizalanmış next round butonu
        right_spacer = tk.Frame(button_frame, bg="#0a6e0a")
        right_spacer.pack(side="left", expand=True, fill="x")
        
        next_round_btn = tk.Button(button_frame, text="Sonraki El", command=self.next_round,
                                   font=self.button_style["font"],
                                   bg=self.button_style["bg"],
                                   fg=self.button_style["fg"],
                                   activebackground=self.button_style["activebackground"],
                                   activeforeground=self.button_style["activeforeground"],
                                   relief=self.button_style["relief"],
                                   borderwidth=self.button_style["borderwidth"],
                                   padx=self.button_style["padx"],
                                   pady=self.button_style["pady"],
                                   width=self.button_style["width"],
                                   height=self.button_style["height"])
        next_round_btn.pack(side="left", padx=15)
        
        # Oyun durumunu güncelle
        self.update_game_state()

        # 0. eli oynamamak için
        if self.game.round == 0:
            self.next_round()
    
    def create_player_ui(self, frame, player_idx, is_human=False):
        player = self.game.players[player_idx]
        player_ui = {"frame": frame}  # Frame referansını kaydet
        
        # Frame kenarındaki çizgileri ekle
        frame.configure(borderwidth=1, relief='solid')
        
        # Daha küçük ve daha iyi düzenlenmiş oyuncu alanı
        info_frame = ttk.Frame(frame, style="Green.TFrame")
        info_frame.pack(fill="x", padx=5, pady=5)
        
        # Stack bilgisi
        player_ui["stack_label"] = ttk.Label(info_frame, text=f"Stack: {player.stack}", font=("Arial", 12), style="Green.TLabel")
        player_ui["stack_label"].pack(side="left", padx=10)
        
        # Bet bilgisi
        player_ui["bet_label"] = ttk.Label(info_frame, text=f"Bet: {player.bet}", font=("Arial", 12), style="Green.TLabel")
        player_ui["bet_label"].pack(side="right", padx=10)
        
        # Kartlar arası mesafeyi artır
        cards_frame = ttk.Frame(frame, style="Green.TFrame")
        cards_frame.pack(pady=10, fill="x")
        
        # Kartları ortalamak için
        cards_container = ttk.Frame(cards_frame, style="Green.TFrame")
        cards_container.pack(side="top", padx=10, pady=5, fill="x", expand=True)
        
        player_ui["card_labels"] = []
        for i in range(2):
            card_img = self.card_images.get("back")  # Varsayılan olarak kart arkası göster
            
            # İnsan oyuncu veya showdown durumunda gerçek kartları göster
            if is_human:
                if i < len(player.hand):
                    card_name = f"{player.hand[i].rank}_of_{player.hand[i].suit}"
                    card_img = self.card_images.get(card_name, self.card_images.get("black_joker"))
            
            # Style Green.TLabel ile etiket oluştur
            card_label = ttk.Label(cards_container, image=card_img, style="Green.TLabel")
            card_label.pack(side="left", padx=5, pady=2)  # padx ve pady değerlerini küçülttüm
            player_ui["card_labels"].append(card_label)
        
        return player_ui
    
    def update_game_state(self):
        # Oyun durumunu güncelle
        
        # Pot ve round bilgisi
        self.pot_label.config(text=f"Pot: {self.game.pot}")
        self.round_label.config(text=f"El: {self.game.round}/{self.settings['max_round']}")
        
        # Community kartlar
        for i, label in enumerate(self.community_card_labels):
            if i < len(self.game.community_cards):
                card = self.game.community_cards[i]
                card_name = f"{card.rank}_of_{card.suit}"
                label.config(image=self.card_images.get(card_name, self.card_images.get("black_joker")))
            else:
                label.config(image=self.card_images.get("black_joker"))
        
        # Oyuncular
        for player_idx, player in enumerate(self.game.players):
            player_ui = self.player_frames.get(player_idx)
            if player_ui:
                # Stack ve bet bilgisi
                player_ui["stack_label"].config(text=f"Stack: {player.stack}")
                player_ui["bet_label"].config(text=f"Bet: {player.bet}")
                
                # Kartlar
                for i, card_label in enumerate(player_ui["card_labels"]):
                    if player_idx == 0:  # İnsan oyuncu
                        if i < len(player.hand):
                            card = player.hand[i]
                            card_name = f"{card.rank}_of_{card.suit}"
                            card_label.config(image=self.card_images.get(card_name, self.card_images.get("black_joker")))
                    else:  # AI oyuncu
                        if player.is_folded:
                            # Fold yapan oyuncu için kart görünmez yap
                            card_label.config(image="")
                        elif self.is_showdown_state():  # Showdown durumu
                            # Showdown'da kartları göster
                            if i < len(player.hand):
                                card = player.hand[i]
                                card_name = f"{card.rank}_of_{card.suit}"
                                card_label.config(image=self.card_images.get(card_name, self.card_images.get("black_joker")))
                        else:
                            # Normal oyun durumunda kart arkası göster
                            card_label.config(image=self.card_images.get("black_joker"))
        
        # Butonların görünürlüğünü ve renklerini ayarla - İnsan oyuncunun sırası ve durumuna göre
        player = self.game.players[0]
        call_amount = self.game.current_bet - player.bet
        
        if hasattr(self, "check_btn") and hasattr(self, "call_btn") and hasattr(self, "fold_btn") and hasattr(self, "raise_btn"):
            # İnsan oyuncunun sırasını belirle
            is_human_turn = False
            
            # ÖNEMLİ DEĞİŞİKLİK: Aktif sıranın insan oyuncusuna gelip gelmediğini kontrol et
            if hasattr(self, "betting_order") and hasattr(self, "current_betting_idx"):
                if len(self.betting_order) > self.current_betting_idx:
                    current_player = self.betting_order[self.current_betting_idx]
                    if current_player.is_human:
                        is_human_turn = True
            
            # İnsan oyuncu fold yaptıysa tüm butonları devre dışı bırak
            if player.is_folded or player.stack <= 0:
                self.fold_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                   disabledforeground=self.disabled_button_style["disabledforeground"])
                self.check_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                    disabledforeground=self.disabled_button_style["disabledforeground"])
                self.call_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                   disabledforeground=self.disabled_button_style["disabledforeground"])
                self.raise_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                    disabledforeground=self.disabled_button_style["disabledforeground"])
            else:
                # Fold butonu - insan sırası ise aktif yap
                if is_human_turn:
                    self.fold_btn.config(state="normal", bg=self.button_style["bg"], fg=self.button_style["fg"])
                else:
                    self.fold_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                       disabledforeground=self.disabled_button_style["disabledforeground"])
                
                # Check/Call butonları - insan sırası ve call miktarı durumuna göre
                if is_human_turn:
                    if call_amount <= 0:
                        # Check yapabilir
                        self.check_btn.config(state="normal", bg=self.button_style["bg"], fg=self.button_style["fg"])
                        self.call_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                           disabledforeground=self.disabled_button_style["disabledforeground"])
                    else:
                        # Call yapmalı
                        self.check_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                            disabledforeground=self.disabled_button_style["disabledforeground"])
                        self.call_btn.config(state="normal", text=f"Call ({call_amount})", 
                                           bg=self.button_style["bg"], fg=self.button_style["fg"])
                else:
                    # İnsan sırası değilse tüm butonlar devre dışı
                    self.check_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                        disabledforeground=self.disabled_button_style["disabledforeground"])
                    if call_amount > 0:
                        self.call_btn.config(state="disabled", text=f"Call ({call_amount})", 
                                           bg=self.disabled_button_style["bg"], 
                                           disabledforeground=self.disabled_button_style["disabledforeground"])
                    else:
                        self.call_btn.config(state="disabled", text="Call", 
                                           bg=self.disabled_button_style["bg"], 
                                           disabledforeground=self.disabled_button_style["disabledforeground"])
                
                # Raise butonu - insan sırası ve stacki yeterliyse aktif yap
                if is_human_turn and player.stack > 0:
                    self.raise_btn.config(state="normal", bg=self.button_style["bg"], fg=self.button_style["fg"])
                else:
                    self.raise_btn.config(state="disabled", bg=self.disabled_button_style["bg"], 
                                        disabledforeground=self.disabled_button_style["disabledforeground"])
        
        # Raise spinbox'ı güncelle
        if hasattr(self, "raise_entry") and hasattr(self, "min_raise_label"):
            min_raise = max(self.game.small_blind, self.game.current_bet - player.bet)
            max_raise = player.stack
            
            # Min raise etiketini güncelle
            self.min_raise_label.config(text=f"Min: {min_raise}")
            
            # Spinbox değerlerini güncelle - all-in durumunda hata oluşmasını engelle
            if min_raise > 0 and max_raise > 0 and min_raise <= max_raise:
                self.raise_entry.config(from_=min_raise, to=max_raise)
                if self.raise_var.get() < min_raise:
                    self.raise_var.set(min_raise)
            elif max_raise <= 0:
                # Stack 0 veya daha az ise, spinbox'ı devre dışı bırak
                self.raise_entry.config(state="disabled")
            elif min_raise > max_raise:
                # min_raise, max_raise'den büyükse, max_raise değerini kullan (all-in durumu)
                self.raise_entry.config(from_=max_raise, to=max_raise)
                self.raise_var.set(max_raise)
        
        # Sırası gelen oyuncuyu sarı çerçeve ile vurgula
        if hasattr(self, "betting_order") and hasattr(self, "current_betting_idx"):
            if self.betting_order and self.current_betting_idx < len(self.betting_order):
                current_player = self.betting_order[self.current_betting_idx]
                
                # Tüm oyuncuların çerçevelerini normal renge çevir
                for player_idx, player_ui in self.player_frames.items():
                    frame = player_ui.get("frame", None)
                    if frame:
                        frame.configure(style="Green.TLabelframe")
                        
                # Sırası gelen oyuncunun çerçevesini sarı yap
                for player_idx, player in enumerate(self.game.players):
                    if player == current_player:
                        player_ui = self.player_frames.get(player_idx)
                        if player_ui:
                            frame = player_ui.get("frame", None)
                            if frame:
                                frame.configure(style="ActivePlayer.TLabelframe")
        
        # Sonsuz döngüye neden olduğu için kaldırdık
        # return self.check_allin_showdown()
    
    def is_showdown_state(self):
        """Showdown durumunda mıyız kontrol et"""
        # Eğer 5 community kart açıldıysa ve bahis turu bittiyse showdown durumundayız
        if len(self.game.community_cards) == 5:
            # Eğer bahis turu tamamlandıysa (tüm bahisler eşit ve herkes aksiyon almış)
            if hasattr(self, "player_acted") and all(self.player_acted.get(p, True) for p in self.game.players if not p.is_folded and p.stack > 0):
                return True
        return False
    
    def fold_action(self):
        """İnsan oyuncu fold yaptı"""
        player = self.game.players[0]
        
        # Oyuncu fold yapmışsa işlem yapamaz
        if player.is_folded:
            messagebox.showwarning("İşlem Yapılamaz", "Zaten fold yaptınız!")
            return
            
        # Fold işlemini uygula
        player.is_folded = True
        self.add_log(f"{player.name} fold yaptı.")
        
        # Oyuncunun aksiyon aldığını işaretle
        self.player_acted[player] = True
        
        # UI'ı güncelle
        self.update_game_state()
        
        # Aktif oyuncu sayısını kontrol et
        active_players = [p for p in self.game.players if not p.is_folded]
        if len(active_players) <= 1:
            self.add_log("Sadece bir oyuncu kaldığı için el sonlandırıldı.")
            self.showdown()
            return
        
        # Eğer all-in durumu varsa direk showdown'a geç
        if self.check_allin_showdown():
            return
        
        # Bahis turu tamamlandı mı kontrol et
        if self.is_betting_round_complete():
            self.next_stage()
            return
        
        # Bir sonraki oyuncuya geç
        self.current_betting_idx = (self.current_betting_idx + 1) % len(self.betting_order)
        
        # Butonları güncelle
        self.update_game_state()
        
        # AI oyuncularının sırasına geç - İnsan oyuncu işlemlerinin sonunda bu çağrı şart!
        self.root.after(100, self.ai_turn)
    
    def call_action(self):
        """İnsan oyuncu call veya check yaptı"""
        player = self.game.players[0]
        
        # Oyuncu fold yapmışsa veya stacki 0 ise işlem yapamaz
        if player.is_folded:
            messagebox.showwarning("İşlem Yapılamaz", "Fold yaptınız!")
            return
            
        if player.stack <= 0:
            messagebox.showwarning("İşlem Yapılamaz", "All-in durumundasınız!")
            return
            
        # Aktif oyuncular ve mevcut max bet
        active_players = [p for p in self.game.players if not p.is_folded]
        max_bet = max(player.bet for player in active_players)
        call_amount = max_bet - player.bet
        
        if call_amount <= 0:
            # Check yapıldı
            self.add_log(f"{player.name} check yaptı.")
        else:
            # Call yapıldı
            if call_amount >= player.stack:
                # All-in
                call_amount = player.stack
                self.add_log(f"{player.name} {call_amount} chip ile all-in yaptı.")
                player.stack = 0
            else:
                self.add_log(f"{player.name} {call_amount} chip ile call yaptı.")
                player.stack -= call_amount
                
            player.bet += call_amount
            self.game.pot += call_amount
            self.game.current_bet = max(self.game.current_bet, player.bet)
        
        # Stack'in 0'dan küçük olmasını engelle
        if player.stack < 0:
            player.stack = 0
            
        # Oyuncunun aksiyon aldığını işaretle
        self.player_acted[player] = True
        
        # UI'ı güncelle
        self.update_game_state()
        
        # Eğer all-in durumu varsa direk showdown'a geç
        if self.check_allin_showdown():
            return
        
        # Bahis turu tamamlandı mı kontrol et
        if self.is_betting_round_complete():
            self.next_stage()
            return
        
        # Bir sonraki oyuncuya geç
        self.current_betting_idx = (self.current_betting_idx + 1) % len(self.betting_order)
        
        # Butonları güncelle
        self.update_game_state()
        
        # AI oyuncularının sırasına geç - İnsan oyuncu işlemlerinin sonunda bu çağrı şart!
        self.root.after(100, self.ai_turn)
    
    def raise_action(self):
        """İnsan oyuncu raise yaptı"""
        player = self.game.players[0]
        
        # Oyuncu fold yapmışsa veya stacki 0 ise işlem yapamaz
        if player.is_folded or player.stack <= 0:
            messagebox.showwarning("İşlem Yapılamaz", "Fold yaptınız veya yeterli stack'iniz kalmadı!")
            return
            
        raise_amount = self.raise_var.get()
        
        # 0 ile raise yapılamamalı kontrolü
        if raise_amount <= 0:
            messagebox.showwarning("Geçersiz Raise", "Raise miktarı 0 veya negatif olamaz!")
            return
            
        # Minimum raise miktarı kontrolü
        active_players = [p for p in self.game.players if not p.is_folded]
        max_bet = max(p.bet for p in active_players)
        min_raise = max(self.game.small_blind, max_bet - player.bet)
        
        # Toplam bet miktarı (player.bet + raise_amount) mevcut max bet'ten büyük olmalı
        if player.bet + raise_amount <= max_bet:
            messagebox.showwarning("Geçersiz Raise", f"Raise miktarı en az {min_raise} olmalıdır!")
            return
            
        if raise_amount > player.stack:
            messagebox.showwarning("Yetersiz Stack", f"En fazla {player.stack} chip ile raise yapabilirsiniz!")
            return
            
        # Raise işlemini uygula
        total_amount = raise_amount + (max_bet - player.bet)  # Call + raise
        player.stack -= total_amount
        player.bet = max_bet + raise_amount
        self.game.current_bet = player.bet
        self.game.pot += total_amount
        
        # Stack'in 0'dan küçük olmasını engelle
        if player.stack < 0:
            player.stack = 0
            
        if player.stack == 0:
            self.add_log(f"{player.name} {raise_amount} chip ile all-in yaptı.")
        else:
            self.add_log(f"{player.name} {raise_amount} chip ile raise yaptı.")
        
        # Raise yapıldığında, tüm diğer oyuncuların aksiyonu sıfırla
        # Herkes tekrar aksiyon almalı
        for p in self.player_acted:
            if p != player and p.stack > 0 and not p.is_folded:
                self.player_acted[p] = False
        
        # Oyuncunun aksiyon aldığını işaretle
        self.player_acted[player] = True
        
        # UI'ı güncelle
        self.update_game_state()
        
        # Eğer all-in durumu varsa direk showdown'a geç
        if self.check_allin_showdown():
            return
        
        # Bahis turu tamamlandı mı kontrol et
        if self.is_betting_round_complete():
            self.next_stage()
            return
        
        # Bir sonraki oyuncuya geç
        self.current_betting_idx = (self.current_betting_idx + 1) % len(self.betting_order)
        
        # Butonları güncelle
        self.update_game_state()
        
        # AI oyuncularının sırasına geç - İnsan oyuncu işlemlerinin sonunda bu çağrı şart!
        self.root.after(100, self.ai_turn)
    
    def ai_turn(self):
        """AI oyuncuların sırasını yönet"""
        # Oyunda aktif kaç oyuncu kaldığını kontrol et
        active_players = [p for p in self.game.players if not p.is_folded]
        if len(active_players) <= 1:
            # Sadece bir oyuncu kaldıysa showdown'a geç
            self.add_log("Sadece bir oyuncu kaldığı için el sonlandırıldı.")
            self.showdown()
            return
        
        # Bahis turu tamamlandı mı kontrol et
        if self.is_betting_round_complete():
            # Bir sonraki aşamaya geç
            self.next_stage()
            return
        
        # Şu anki aktif oyuncuları güncelle
        active_players = [p for p in self.game.players if not p.is_folded and p.stack > 0]
        
        # Eğer betting_order yoksa veya boşsa, yeniden oluştur
        if not hasattr(self, "betting_order") or not self.betting_order:
            dealer_idx = self.game.round % len(self.game.players)
            next_idx = -1
            
            # Post-flop turlarında ilk sözü dealer'dan sonraki ilk aktif oyuncuya ver
            if len(self.game.community_cards) > 0:
                for i in range(1, len(self.game.players) + 1):
                    check_idx = (dealer_idx + i) % len(self.game.players)
                    player = self.game.players[check_idx]
                    if not player.is_folded and player.stack > 0:
                        next_idx = check_idx
                        break
            else:
                # Pre-flop'ta big blind'dan sonraki oyuncudan başla
                next_idx = (dealer_idx + 3) % len(self.game.players)
                
            # Bahis sırasını oluştur
            self.betting_order = []
            for i in range(len(self.game.players)):
                check_idx = (next_idx + i) % len(self.game.players)
                player = self.game.players[check_idx]
                if not player.is_folded and player.stack > 0:
                    self.betting_order.append(player)
            
            # Her oyuncunun aksiyonu olduğunu takip etmek için
            self.player_acted = {p: False for p in active_players}
            self.current_betting_idx = 0
        
        # Şu anki oyuncuyu al
        if self.current_betting_idx >= len(self.betting_order):
            self.current_betting_idx = 0
            
        current_player = self.betting_order[self.current_betting_idx]
        
        # İnsan oyuncu sırası mı?
        if current_player.is_human:
            # İnsan oyuncunun UI'da butonları aktif et - log mesajı kaldırıldı
            self.update_game_state()
            return
        
        # AI oyuncusunun aksiyonunu işle
        if current_player.stack <= 0:
            self.add_log(f"{current_player.name} zaten all-in durumunda.")
            self.player_acted[current_player] = True
            # Bir sonraki oyuncuya geç
            self.current_betting_idx = (self.current_betting_idx + 1) % len(self.betting_order)
            self.root.after(10, self.ai_turn)
            return
        
        # Mevcut durum analizi
        is_check_round = all(player.bet == 0 for player in active_players)
        max_bet = max(player.bet for player in active_players)
        
        # AI'nın aksiyonunu al
        action = current_player.get_action(self.game)
        
        # İlk tur tüm bahisler 0 ise check yap
        if is_check_round and (action == "call"):
            action = "check"
        
        # İlk tur fold gelirse %70 ihtimalle check yap (agresiflik ayarı)
        if is_check_round and action == "fold":
            if random.random() < 0.7:  # %70 ihtimalle check
                action = "check"
        
        # Aksiyonu işle
        if action == "fold":
            current_player.is_folded = True
            self.add_log(f"{current_player.name} fold yaptı.")
        elif action == "check":
            # Check aksiyonu - bet = 0 durumunda
            if max_bet > 0 and current_player.bet < max_bet:
                # Aslında check yapamaz, call yapmalı
                call_amount = min(max_bet - current_player.bet, current_player.stack)
                current_player.stack -= call_amount
                current_player.bet += call_amount
                self.game.pot += call_amount
                
                # Stack'in 0'dan küçük olmasını engelle
                if current_player.stack < 0:
                    current_player.stack = 0
                
                if current_player.stack == 0:
                    self.add_log(f"{current_player.name} {call_amount} chip ile all-in yaptı.")
                else:
                    self.add_log(f"{current_player.name} {call_amount} chip ile call yaptı.")
            else:
                # Normal check
                self.add_log(f"{current_player.name} check yaptı.")
        elif action == "call":
            call_amount = max_bet - current_player.bet
            if call_amount <= 0:
                # Aslında check yapmalı
                self.add_log(f"{current_player.name} check yaptı.")
            elif call_amount <= current_player.stack:
                current_player.stack -= call_amount
                current_player.bet += call_amount
                self.game.pot += call_amount
                
                # Stack'in 0'dan küçük olmasını engelle
                if current_player.stack < 0:
                    current_player.stack = 0
                    
                self.add_log(f"{current_player.name} {call_amount} chip ile call yaptı.")
            else:
                # All-in durumu
                self.add_log(f"{current_player.name} yeterli chip'i olmadığı için {current_player.stack} chip ile all-in yapıyor.")
                self.game.pot += current_player.stack
                current_player.bet += current_player.stack
                current_player.stack = 0
        elif action == "raise":
            raise_amount = current_player.get_raise_amount(self.game)
            
            # Raise miktarı 0 veya negatif olamaz
            if raise_amount <= 0:
                # Raise yapamayacaksa check ya da call yap
                if is_check_round:
                    self.add_log(f"{current_player.name} check yaptı.")
                else:
                    # Check round değilse call yap
                    call_amount = min(max_bet - current_player.bet, current_player.stack)
                    if call_amount > 0:
                        current_player.stack -= call_amount
                        current_player.bet += call_amount
                        self.game.pot += call_amount
                        
                        # Stack'in 0'dan küçük olmasını engelle
                        if current_player.stack < 0:
                            current_player.stack = 0
                            
                        self.add_log(f"{current_player.name} raise yapamadığı için {call_amount} chip ile call yaptı.")
                    else:
                        self.add_log(f"{current_player.name} check yaptı.")
            else:
                # Raise miktarı pozitif olduğunda raise işlemi gerçekleştir
                # Minimum raise miktarı kontrolü (en az small blind kadar olmalı)
                min_raise = max(self.game.small_blind, max_bet - current_player.bet)
                
                # Toplam bet miktarı (current_player.bet + raise_amount) current_bet'ten büyük olmalı
                if current_player.bet + raise_amount <= max_bet:
                    raise_amount = min_raise
                
                # Maksimum miktarı stack ile sınırla
                raise_amount = min(raise_amount, current_player.stack)
                
                # Normal raise - önceki bahisleri de ekle
                total_amount = raise_amount + (max_bet - current_player.bet)
                current_player.stack -= total_amount
                current_player.bet = max_bet + raise_amount
                self.game.current_bet = current_player.bet
                self.game.pot += total_amount
                
                # Stack'in 0'dan küçük olmasını engelle
                if current_player.stack < 0:
                    current_player.stack = 0
                
                if current_player.stack == 0:
                    self.add_log(f"{current_player.name} {raise_amount} chip ile all-in yaptı.")
                else:
                    self.add_log(f"{current_player.name} {raise_amount} chip ile raise yaptı.")
                    
                # Raise yapıldığında, tüm diğer oyuncuların aksiyonu sıfırla
                # Herkes tekrar aksiyon almalı
                for player in self.player_acted:
                    if player != current_player and player.stack > 0 and not player.is_folded:
                        self.player_acted[player] = False
        
        # Oyuncunun aksiyon aldığını işaretle
        self.player_acted[current_player] = True
        
        # UI'ı güncelle
        self.update_game_state()
        self.root.update()
        
        # Oyun durumunu yeniden kontrol et
        active_players = [p for p in self.game.players if not p.is_folded]
        if len(active_players) <= 1:
            # Sadece bir oyuncu kaldıysa showdown'a geç
            self.add_log("Sadece bir oyuncu kaldığı için el sonlandırıldı.")
            self.showdown()
            return
        
        # Eğer all-in durumu varsa direk showdown'a geç
        if self.check_allin_showdown():
            return
        
        # Bahis turu tamamlandı mı kontrol et
        if self.is_betting_round_complete():
            # Bir sonraki aşamaya geç
            self.next_stage()
            return
        
        # Sonraki oyuncuya geç
        self.current_betting_idx = (self.current_betting_idx + 1) % len(self.betting_order)
        
        # AI hamleleri arasında kısa bir gecikme ekle - 100ms
        self.root.after(100, self.ai_turn)
    
    def is_betting_round_complete(self):
        """Bahis turu tamamlandı mı kontrol et - aktif oyuncular en az 1 aksiyon aldı ve tüm bahisler eşit"""
        active_players = [p for p in self.game.players if not p.is_folded and p.stack > 0]
        
        # 1. Tüm oyuncular aksiyon aldı mı kontrol et
        for player in active_players:
            if not self.player_acted.get(player, False):
                return False
        
        # 2. Tüm bahisler eşit mi kontrol et
        if not self.game.is_betting_round_done():
            return False
        
        # Evet, bahis turu tamamlandı
        return True
    
    def next_stage(self):
        """Bir sonraki aşamaya geç (flop, turn, river)"""
        # Oyunda aktif kaç oyuncu kaldığını kontrol et
        active_players = [p for p in self.game.players if not p.is_folded]
        if len(active_players) <= 1:
            # Sadece bir oyuncu kaldıysa showdown'a geç
            self.add_log("Sadece bir oyuncu kaldığı için el sonlandırıldı.")
            self.showdown()
            return
            
        # Bir sonraki aşamaya geç
        if len(self.game.community_cards) == 0:
            # Flop
            self.game.deal_community_cards(3)
            self.add_log("--- FLOP ---")
            flop_cards = [f"{card.rank} of {card.suit}" for card in self.game.community_cards]
            self.add_log(f"Flop kartları: {', '.join(flop_cards)}")
        elif len(self.game.community_cards) == 3:
            # Turn
            self.game.deal_community_cards(1)
            self.add_log("--- TURN ---")
            turn_card = self.game.community_cards[3]
            self.add_log(f"Turn kartı: {turn_card.rank} of {turn_card.suit}")
        elif len(self.game.community_cards) == 4:
            # River
            self.game.deal_community_cards(1)
            self.add_log("--- RIVER ---")
            river_card = self.game.community_cards[4]
            self.add_log(f"River kartı: {river_card.rank} of {river_card.suit}")
        else:
            # Showdown
            self.add_log("--- SHOWDOWN ---")
            self.showdown()
            return
        
        # Bahisleri sıfırla
        for player in self.game.players:
            player.bet = 0
        self.game.current_bet = 0
            
        # UI'ı güncelle
        self.update_game_state()
        
        # Aktif oyuncular (stack > 0 ve fold olmamış)
        active_players = [p for p in self.game.players if not p.is_folded and p.stack > 0]
        if not active_players:
            # Aktif oyuncu yoksa (tüm oyuncular all-in)
            self.next_stage()
            return
        
        # Dealer'ı bul
        dealer_idx = self.game.round % len(self.game.players)
        
        # Post-flop turlarında ilk sözü dealer'dan sonraki ilk aktif oyuncuya ver
        next_idx = -1
        for i in range(1, len(self.game.players) + 1):
            check_idx = (dealer_idx + i) % len(self.game.players)
            player = self.game.players[check_idx]
            if not player.is_folded and player.stack > 0:
                next_idx = check_idx
                break
        
        # Eğer aktif oyuncu bulunamazsa (hepsi all-in)
        if next_idx == -1:
            # Bir sonraki aşamaya geç
            self.next_stage()
            return
        
        # Bahis turundaki sırayı belirle
        self.betting_order = []
        # Aktif oyuncuları sırala
        for i in range(len(self.game.players)):
            check_idx = (next_idx + i) % len(self.game.players)
            player = self.game.players[check_idx]
            if not player.is_folded and player.stack > 0:
                self.betting_order.append(player)
        
        # Her oyuncunun aksiyonu olduğunu takip etmek için
        self.player_acted = {p: False for p in active_players}
        self.current_betting_idx = 0
        
        # UI'ı güncelle
        self.update_game_state()
        
        # Bahis turuna başla
        self.ai_turn()
    
    def showdown(self):
        # Showdown - kazananı belirle
        active_players = [p for p in self.game.players if not p.is_folded]
        
        # All-in kontrolü - yan pot hesaplama için gereken bilgileri toplama
        all_in_players = [p for p in active_players if p.stack == 0]
        has_all_in = len(all_in_players) > 0
        
        # Showdown'da tüm kartları göster
        # Tüm AI kartlarını görünür yap
        for player_idx, player in enumerate(self.game.players):
            if not player.is_folded:  # Fold yapmamış tüm oyuncular (AI ve insan)
                player_ui = self.player_frames.get(player_idx)
                if player_ui and "card_labels" in player_ui:
                    for i, card_label in enumerate(player_ui["card_labels"]):
                        if i < len(player.hand):
                            card = player.hand[i]
                            card_name = f"{card.rank}_of_{card.suit}"
                            card_image = self.card_images.get(card_name, self.card_images.get("black_joker"))
                            card_label.configure(image=card_image)
                            # Kartın görüntüsünü hemen güncelle
                            self.root.update_idletasks()
        
        # UI'ı güncelle - çağrı değiştirildi, direkt showdown_state'i True yapıyoruz
        # update_game_state() yerine burada yapıyoruz (loop engellemek için)
        self.pot_label.config(text=f"Pot: {self.game.pot}")
        self.round_label.config(text=f"El: {self.game.round}/{self.settings['max_round']}")
        self.root.update()
        
        # El değerlendirmesini hazırla ve loga ekle
        self.add_log("--- EL DEĞERLENDİRMESİ ---")
        
        # Player hands bilgisini topla
        player_hands = []
        
        if len(active_players) <= 1:
            # Tek kalan oyuncu
            if active_players:
                winner = active_players[0]
                self.add_log(f"Kazanan: {winner.name} (Tek kalan oyuncu)")
                self.add_log(f"{winner.name} {self.game.pot} chip kazandı!")
                winner.stack += self.game.pot
                self.game.pot = 0
            else:
                self.add_log("Oyunda kimse kalmadı!")
        else:
            # Her oyuncunun elini değerlendir
            for player in active_players:
                score = el_gucu_hesapla(player.hand, self.game.community_cards)
                player_hands.append((player, score))
                hand_desc = self.describe_hand(score)
                self.add_log(f"{player.name}'in eli: {hand_desc}")
                
            # En düşük skor en iyi el (treys'te 1 en iyi, 7462 en kötü)
            player_hands.sort(key=lambda x: x[1])
            winner = player_hands[0][0]
            hand_desc = self.describe_hand(player_hands[0][1])
            self.add_log(f"Kazanan: {winner.name} ile {hand_desc}")
            
            # Yan pot hesaplama - all-in oyuncular varsa
            if has_all_in:
                self.calculate_side_pots(active_players, player_hands)
            else:
                # Normal pot için kazananı belirle
                winner.stack += self.game.pot
                self.add_log(f"{winner.name} {self.game.pot} chip kazandı!")
                self.game.pot = 0
        
        # Oyun durumunu güncelle
        self.update_game_state()  # Şimdi burada çağırıyoruz
        
        # Bankrupt oyuncuları kontrol et
        self.check_bankrupt_players()
    
    def check_bankrupt_players(self):
        """Stacki 0 olan oyuncuları kontrol et"""
        # Stacki 0 olan oyuncuları kontrol et (sonraki elde fold olacaklar)
        for player in self.game.players:
            if player.stack <= 0 and not player.is_folded:
                self.add_log(f"{player.name} chip'i kalmadığı için bir sonraki elde oynayamayacak.")
        
        self.update_game_state()
        
        # Oyunun bitip bitmediğini kontrol et
        active_count = sum(1 for p in self.game.players if p.stack > 0)
        if active_count <= 1:
            self.add_log("Yeterli aktif oyuncu kalmadığı için oyun sona erdi.")
            self.end_game()
            return
    
    def calculate_side_pots(self, active_players, player_hands):
        """Yan pot hesaplama"""
        # Önce oyuncuları kartlarına göre sırala
        player_hand_map = {p[0]: p[1] for p in player_hands}
        
        # Oyuncuları bet miktarına göre sırala (düşükten yükseğe)
        players_by_bet = sorted(active_players, key=lambda p: p.bet)
        
        # Toplam pot ve kümülatif oyuncu grupları
        total_pot = self.game.pot
        remaining_pot = total_pot
        prev_bet = 0
        
        self.add_log(f"Toplam pot: {total_pot}")
        
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
                                
                            hand_desc = self.describe_hand(player_hand_map.get(winner, 7462))
                            pot_desc = f"Pot (Bet: {current_bet})" if i < len(players_by_bet) - 1 else "Ana Pot"
                            self.add_log(f"{pot_desc} kazananı: {winner.name} ile {hand_desc}, Kazanç: {winner_share}")
                            winner.stack += winner_share
            
            prev_bet = current_bet
                    
        # Pot'u sıfırla
        self.game.pot = 0
    
    def describe_hand(self, score):
        """Treys kütüphanesinin ürettiği skor değerini insan tarafından okunabilir bir el tanımına dönüştürür"""
        if score == 1:
            return "Royal Flush"
        elif score <= 10:
            return "Straight Flush"
        elif score <= 166:
            return "Four of a Kind"
        elif score <= 322:
            return "Full House"
        elif score <= 1599:
            return "Flush"
        elif score <= 1609:
            return "Straight"
        elif score <= 2467:
            return "Three of a Kind"
        elif score <= 3325:
            return "Two Pair"
        elif score <= 6185:
            return "One Pair"
        else:
            return "High Card"
    
    def next_round(self):
        """Bir sonraki ele geç"""
        self.game.round += 1
        
        if self.game.round > self.settings["max_round"]:
            self.end_game()
            return
            
        self.add_log(f"\n=== EL {self.game.round} ===")
        
        # Önceki eli temizle
        self.game.reset_round()
        
        # Stack'i 0 olan oyuncuları oyundan kaldır
        if self.game.remove_bankrupt_players():
            # Bankrupt oyuncuları log'a ekle
            for player_idx in list(self.player_frames.keys()):
                found = False
                for idx, player in enumerate(self.game.players):
                    if idx == player_idx:
                        found = True
                        break
                        
                if not found and player_idx in self.player_frames:
                    # Bu oyuncu artık oyunda değil
                    if player_idx in self.player_frames and "frame" in self.player_frames[player_idx]:
                        player_frame = self.player_frames[player_idx]["frame"]
                        if player_frame:
                            player_name = player_frame.cget("text")
                            self.add_log(f"{player_name} chip'i kalmadığı için oyundan ayrıldı.")
                            player_frame.pack_forget()  # Frame'i gizle
                            
        # Eğer oyuncu sayısı 2'den az kaldıysa oyunu bitir
        if len(self.game.players) < 2:
            self.add_log("Yeterli oyuncu kalmadığı için oyun sona erdi.")
            self.end_game()
            return
        
        # Yeni kartları dağıt
        self.game.deck.shuffle()
        self.game.deal_hole_cards()
        
        # Eğer 0. el ise (gerçekte ilk el) direk sonraki ele geç
        if self.game.round == 0:
            self.next_round()
            return
        
        # Oyuncuların kartlarını log'a kaydet
        player = self.game.players[0]  # İnsan oyuncu
        hand_cards = [f"{card.rank} of {card.suit}" for card in player.hand]
        self.add_log(f"Kartlarınız: {', '.join(hand_cards)}")
        
        # Aktif oyuncuları belirle (Stack > 0)
        active_players = [p for p in self.game.players if p.stack > 0]
        if len(active_players) <= 1:
            # Sadece bir oyuncu kaldıysa oyunu bitir
            self.end_game()
            return
            
        # Aktif oyuncular arasından dealer, small blind ve big blind pozisyonlarını belirle
        # Her el için pozisyonları değiştir (dealer = round % active_count)
        active_count = len(active_players)
        dealer_idx = self.game.round % active_count
        sb_idx = (dealer_idx + 1) % active_count
        bb_idx = (dealer_idx + 2) % active_count
        
        # Small blind ve big blind oyuncularını al
        small_blind_player = active_players[sb_idx]
        big_blind_player = active_players[bb_idx]
        
        # Small blind yerleştir
        small_blind_amount = min(self.game.small_blind, small_blind_player.stack)
        self.game.place_bet(small_blind_player, small_blind_amount)
        self.add_log(f"{small_blind_player.name} small blind: {small_blind_amount}")
        
        # Big blind yerleştir
        big_blind_amount = min(self.game.small_blind * 2, big_blind_player.stack)
        self.game.place_bet(big_blind_player, big_blind_amount)
        self.add_log(f"{big_blind_player.name} big blind: {big_blind_amount}")
        
        # Current bet'i büyük blind olarak ayarla
        self.game.current_bet = big_blind_amount
        
        # UI'ı güncelle
        self.update_game_state()
        
        # All-in durumunu kontrol et ve ilgili oyuncuların fold durumunu düzelt
        for player in self.game.players:
            if player.stack <= 0 and player.bet > 0:  # All-in durumu
                player.is_folded = False  # All-in oyuncusu fold değil
                self.add_log(f"{player.name} all-in durumunda, el sonuna kadar oyunda kalacak.")
            else:
                # Diğer oyuncuların fold durumunu resetle (yeni el)
                player.is_folded = False
        
        # Pre-flop için betting_order oluştur
        dealer_pos = self.game.round % len(self.game.players)
        # Big blind'dan sonraki pozisyondan başla
        start_pos = (dealer_pos + 3) % len(self.game.players)
        
        self.betting_order = []
        for i in range(len(self.game.players)):
            check_idx = (start_pos + i) % len(self.game.players)
            player = self.game.players[check_idx]
            if not player.is_folded and player.stack > 0:
                self.betting_order.append(player)
        
        # Her oyuncunun aksiyonu olduğunu takip etmek için
        self.player_acted = {p: False for p in active_players}
        
        # Small blind ve big blind oyuncuları aksiyon aldı sayalım
        # Ama raise yapılırsa tekrar aksiyon almaları gerekecek
        if small_blind_player in self.player_acted:
            self.player_acted[small_blind_player] = True
        if big_blind_player in self.player_acted:
            self.player_acted[big_blind_player] = True
        
        self.current_betting_idx = 0
        
        # UI'ı güncelle
        self.update_game_state()
        
        # Eğer insan oyuncu sıradaysa bekle, değilse AI turuna geç
        current_player = self.betting_order[self.current_betting_idx] if self.betting_order else None
        if current_player and not current_player.is_human:
            self.ai_turn()
    
    def end_game(self):
        # Oyun bitti, sonuçları göster
        result_text = "Oyun Sonuçları:\n\n"
        
        self.add_log("\n=== OYUN SONUÇLARI ===")
        for player in self.game.players:
            result_text += f"{player.name}: {player.stack} chip\n"
            self.add_log(f"{player.name}: {player.stack} chip")
            
        messagebox.showinfo("Oyun Bitti", result_text)
        
        # Ana menüye dön
        for widget in self.root.winfo_children():
            widget.destroy()
            
        self.setup_screen()
    
    def add_log(self, message):
        """Log ekranına mesaj ekler"""
        if self.log_text:
            self.log_text.insert(tk.END, f"{message}\n")
            self.log_text.see(tk.END)  # Otomatik kaydır
    
    def check_allin_showdown(self):
        """Tüm aktif oyuncular all-in mi kontrol et ve showdown'a geç"""
        # Recursive çağrıları engellemek için flag kontrolü
        if hasattr(self, "_in_allin_check") and self._in_allin_check:
            return False
            
        # İşaretçi ayarla
        self._in_allin_check = True
        
        try:
            active_players = [p for p in self.game.players if not p.is_folded]
            non_allin_players = [p for p in active_players if p.stack > 0]
            
            # Eğer aktif oyunculardan en fazla 1 tanesi non-all-in ise ve bahisler eşitse, kalan kartları açıp showdown'a geç
            if len(non_allin_players) <= 1 and self.game.is_betting_round_done():
                # All-in durumu, bahis turu tamamlanmış ve kalan tek oyuncu var/yok
                self.add_log("All-in durumu tespit edildi. Kalan tüm kartlar açılıyor...")
                
                # Kalan community kartları aç
                while len(self.game.community_cards) < 5:
                    if len(self.game.community_cards) == 0:
                        # Flop açılmadıysa flop aç
                        self.game.deal_community_cards(3)
                        self.add_log("--- FLOP ---")
                        flop_cards = [f"{card.rank} of {card.suit}" for card in self.game.community_cards]
                        self.add_log(f"Flop kartları: {', '.join(flop_cards)}")
                        # Arayüzü güncelle ama recursive çağrıları önle
                        self.pot_label.config(text=f"Pot: {self.game.pot}")
                        self.round_label.config(text=f"El: {self.game.round}/{self.settings['max_round']}")
                        self.root.update()
                        # 1 saniye bekle, kartlar görünsün
                        self.root.after(1000, lambda: None)
                    elif len(self.game.community_cards) == 3:
                        # Turn açılmadıysa turn aç
                        self.game.deal_community_cards(1)
                        self.add_log("--- TURN ---")
                        turn_card = self.game.community_cards[3]
                        self.add_log(f"Turn kartı: {turn_card.rank} of {turn_card.suit}")
                        # Arayüzü güncelle ama recursive çağrıları önle
                        self.pot_label.config(text=f"Pot: {self.game.pot}")
                        self.round_label.config(text=f"El: {self.game.round}/{self.settings['max_round']}")
                        self.root.update()
                        # 1 saniye bekle, kartlar görünsün
                        self.root.after(1000, lambda: None)
                    elif len(self.game.community_cards) == 4:
                        # River açılmadıysa river aç
                        self.game.deal_community_cards(1)
                        self.add_log("--- RIVER ---")
                        river_card = self.game.community_cards[4]
                        self.add_log(f"River kartı: {river_card.rank} of {river_card.suit}")
                        # Arayüzü güncelle ama recursive çağrıları önle
                        self.pot_label.config(text=f"Pot: {self.game.pot}")
                        self.round_label.config(text=f"El: {self.game.round}/{self.settings['max_round']}")
                        self.root.update()
                        # 1 saniye bekle, kartlar görünsün
                        self.root.after(1000, lambda: None)
                
                # Tüm kartlar açıldı, showdown'a geç
                self.add_log("--- SHOWDOWN ---")
                # İşaretçiyi kaldır
                self._in_allin_check = False
                self.showdown()
                return True
            
            return False
        finally:
            # İşaretçiyi kaldır
            self._in_allin_check = False
    
    def run(self):
        self.setup_screen()
        self.root.mainloop()

if __name__ == "__main__":
    ui = PokerUI()
    ui.run() 