import tkinter as tk
import random
import math
import time
import os
import sys

try:
    from PIL import Image, ImageTk, ImageEnhance, ImageSequence
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

def resource_path(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

CELL = 36  
COLS, ROWS = 36, 19
WIDTH, HEIGHT = COLS * CELL, ROWS * CELL

MOVE_DELAY = 120  
FPS_DELAY = 16

STUN_DURATION = 0.8
DECAY_TIME = 10.0
TARGET_SCORE = 300

EVOLUTION_STAGES = [
    {"threshold": 0,   "name": "Utaite Era",    "head": "#1e90ff", "glow": "#00008b", "bg_accent": "#000033", "msg": "THE JOURNEY BEGINS"},
    {"threshold": 150,  "name": "Gira Gira",     "head": "#ff1493", "glow": "#8b008b", "bg_accent": "#330033", "msg": "SHINING BRIGHT!"},
    {"threshold": 300, "name": "Usseewa",       "head": "#dc143c", "glow": "#8b0000", "bg_accent": "#330000", "msg": "REBELLION AWAKENED!"},
    {"threshold": 450, "name": "Legendary Abo", "head": "#00ffff", "glow": "#008b8b", "bg_accent": "#003333", "msg": "GYARUUU..."}
]

class ADOGames:
    def __init__(self, root):
        self.root = root
        self.root.title("Ado's Appetite: Blue Rose Hunt")
        self.canvas = tk.Canvas(root, width=WIDTH, height=HEIGHT, bg="#050508", highlightthickness=0)
        self.canvas.pack()

        self.root.bind("<KeyPress>", self.on_key)
        self.state = "SPLASH"
        self.game_mode = "ENDLESS" 
        self.menu_selection = 0 
        
        self.assets = {}
        self.gif_frames = []
        self.splash_frames = []
        self.gif_index = 0
        self.splash_index = 0
        self.gif_timer = 0.0
        self.splash_timer = 0.0
        self.load_assets()

        self.particles = []
        self.floating_texts = []
        self.obstacles = []
        self.bg_notes = []
        
        for _ in range(15):
            self.bg_notes.append({
                "x": random.randint(0, WIDTH), "y": random.randint(50, HEIGHT),
                "speed": random.uniform(0.3, 0.8), "size": random.randint(14, 24),
                "char": random.choice(["♪", "♫", "", "♩", "", "✦"])
            })
        
        self.shake_frames = 0
        self.max_shake_frames = 1
        self.shake_intensity = 0
        
        self.loop_running = True
        self.main_loop()

    def load_assets(self):
        if not HAS_PIL:
            print("Library Pillow belum terinstal. Fallback ke grafis standar.")
            return

        def process_image(filename, size, darken_factor=1.0):
            full_path = resource_path(filename)
            if os.path.exists(full_path):
                try:
                    img = Image.open(full_path).convert("RGBA")
                    img = img.resize(size, Image.Resampling.LANCZOS)
                    if darken_factor < 1.0:
                        enhancer = ImageEnhance.Brightness(img)
                        img = enhancer.enhance(darken_factor) 
                    return ImageTk.PhotoImage(img)
                except Exception as e:
                    print(f"Gagal memuat {filename}: {e}")
            return None

        pop_size = (260, 260)
        self.assets['gameover_pop'] = process_image("assets/AdoVer.png", pop_size)
        self.assets['pause_pop'] = process_image("assets/AdoPause.png", pop_size)
        self.assets['win_pop'] = process_image("assets/AdoWin.png", pop_size)
        self.assets['exit_pop'] = process_image("assets/AdonotAp.png", pop_size)
        
        self.assets['food_rose'] = process_image("assets/AdoRose.png", (CELL + 4, CELL + 4))
        self.assets['flying_onion'] = process_image("assets/FlyingOnion.png", (CELL + 8, CELL + 8))
        
        crew_size = CELL - 4  
        head_size = CELL + 20
        
        self.assets['crew_chill'] = process_image("assets/AdoChill.png", (crew_size, crew_size))
        self.assets['crew_legend'] = process_image("assets/Abo.png", (crew_size, crew_size))
        
        self.assets['head_chill'] = process_image("assets/AdoChill.png", (head_size, head_size))
        self.assets['head_legend'] = process_image("assets/Abo.png", (head_size, head_size))

        hitori_png = resource_path("assets/HitorixAdo.png")
        hitori_jpg = resource_path("assets/HitorixAdo.jpg")
        hitori_path = hitori_png if os.path.exists(hitori_png) else hitori_jpg
        self.assets['hitori_ado'] = process_image(hitori_path, (200, 200))

        gif_file = resource_path("assets/Abodance.gif")
        if os.path.exists(gif_file):
            try:
                gif = Image.open(gif_file)
                for frame in ImageSequence.Iterator(gif):
                    frame_img = frame.convert("RGBA").resize((WIDTH, HEIGHT), Image.Resampling.LANCZOS)
                    enhancer = ImageEnhance.Brightness(frame_img)
                    frame_img = enhancer.enhance(0.3) 
                    self.gif_frames.append(ImageTk.PhotoImage(frame_img))
            except Exception as e:
                print(f"Gagal memuat GIF Abodance.gif: {e}")
        
        splash_file = resource_path("assets/AdoHello.gif")
        if os.path.exists(splash_file):
            try:
                gif = Image.open(splash_file)
                for frame in ImageSequence.Iterator(gif):
                    frame_img = frame.convert("RGBA").resize((350, 350), Image.Resampling.LANCZOS)
                    enhancer = ImageEnhance.Brightness(frame_img)
                    frame_img = enhancer.enhance(1.1)
                    self.splash_frames.append(ImageTk.PhotoImage(frame_img))
            except Exception as e:
                print(f"Gagal memuat GIF AdoHello.gif: {e}")

    def start_game(self, mode="ENDLESS"):
        self.game_mode = mode
        self.snake = [(8, ROWS//2), (7, ROWS//2), (6, ROWS//2)]
        self.direction = (1, 0)
        self.next_direction = (1, 0)
        self.food = None
        self.obstacles.clear()
        
        self.score = 0
        self.stage_index = 0

        self.last_eat_time = time.time()
        self.last_move_time = time.time()
        self.stun_until = 0.0
        self.decay_active = False

        self.particles.clear()
        self.floating_texts.clear()
        self.flash_timer = 0
        self.evolution_anim_timer = 0
        self.shake_frames = 0

        self.spawn_food()
        self.state = "PLAYING"

    def on_key(self, event):
        key = event.keysym.lower()
        
        if self.state == "SPLASH":
            if key in ["return", "space", "1", "2", "3", "4"]:
                self.state = "MENU"
            return
        
        if self.state == "EXIT_CONFIRM":
            if key in ["1", "y", "return", "space"]:
                self.root.destroy()
            elif key in ["2", "n", "escape", "m"]:
                self.state = "MENU"
            return
        
        if self.state == "MENU":
            if key in ["up", "w"]:
                self.menu_selection = (self.menu_selection - 1) % 4
            elif key in ["down", "s"]:
                self.menu_selection = (self.menu_selection + 1) % 4
            elif key in ["return", "space"]:
                if self.menu_selection == 0:
                    self.start_game(mode="LEVEL")
                elif self.menu_selection == 1:
                    self.start_game(mode="ENDLESS")
                elif self.menu_selection == 2:
                    self.state = "ABOUT"
                elif self.menu_selection == 3:
                    self.state = "EXIT_CONFIRM"
            elif key == "1":
                self.menu_selection = 0
                self.start_game(mode="LEVEL")
            elif key == "2":
                self.menu_selection = 1
                self.start_game(mode="ENDLESS")
            elif key == "3":
                self.menu_selection = 2
                self.state = "ABOUT"
            elif key == "4":
                self.menu_selection = 3
                self.state = "EXIT_CONFIRM"
                
        elif self.state in ["GAMEOVER", "WIN"]:
            if key == "1":
                self.start_game(mode="LEVEL")
            elif key == "2":
                self.start_game(mode="ENDLESS")
            elif key == "m":
                self.state = "MENU"
            
        elif self.state == "ABOUT":
            if key == "m" or key == "escape":
                self.state = "MENU"
            return
            
        elif self.state == "PAUSED":
            if key == "p" or key == "escape":
                self.state = "PLAYING"
                time_paused = time.time() - self.pause_time
                self.last_eat_time += time_paused
                self.last_move_time += time_paused
                if self.stun_until > 0:
                    self.stun_until += time_paused
            elif key == "m":
                self.state = "MENU"
            return

        elif key == "p" or key == "escape":
            if self.state == "PLAYING":
                self.state = "PAUSED"
                self.pause_time = time.time()
            return

        if self.state == "PLAYING":
            key_map = {
                "up": (0, -1), "down": (0, 1), "left": (-1, 0), "right": (1, 0),
                "w": (0, -1), "s": (0, 1), "a": (-1, 0), "d": (1, 0)
            }
            new_dir = key_map.get(key)
            if new_dir:
                if new_dir[0] + self.direction[0] != 0 or new_dir[1] + self.direction[1] != 0:
                    self.next_direction = new_dir

    def spawn_food(self):
        while True:
            pos = (random.randint(0, COLS - 1), random.randint(2, ROWS - 1))
            if pos not in self.snake and pos not in self.obstacles:
                self.food = pos
                break

    def spawn_obstacles(self):
        max_obstacles = self.score // 50
        while len(self.obstacles) < max_obstacles:
            pos = (random.randint(0, COLS - 1), random.randint(2, ROWS - 1))
            hx, hy = self.snake[0]
            dist_to_head = abs(pos[0] - hx) + abs(pos[1] - hy)
            if pos not in self.snake and pos != self.food and pos not in self.obstacles and dist_to_head > 4:
                self.obstacles.append(pos)
                self.spawn_particles(pos[0]*CELL + CELL//2, pos[1]*CELL + CELL//2, "#ff0044", 8, burst=False)

    def trigger_shake(self, frames, intensity):
        self.max_shake_frames = max(1, frames // 2)
        self.shake_frames = frames // 2
        self.shake_intensity = intensity / 3

    def check_evolution(self):
        old_stage = self.stage_index
        for i, stage in enumerate(EVOLUTION_STAGES):
            if self.score >= stage["threshold"]:
                self.stage_index = i
                
        if self.stage_index > old_stage:
            self.evolution_anim_timer = 2.0
            self.trigger_shake(15, 4)
            stage = EVOLUTION_STAGES[self.stage_index]
            self.spawn_particles(WIDTH // 2, HEIGHT // 2, stage["head"], 60, burst=True)
            self.flash_timer = 0.2

    def spawn_particles(self, x, y, color, count, burst=False):
        for _ in range(count):
            speed_mult = 2.0 if burst else 0.8
            self.particles.append({
                "x": x, "y": y, "vx": random.uniform(-3, 3) * speed_mult, "vy": random.uniform(-3, 3) * speed_mult,
                "life": 1.0, "color": color, "size": random.uniform(3, 5)
            })

    def add_floating_text(self, x, y, text, color, size=14):
        self.floating_texts.append({"x": x, "y": y, "text": text, "color": color, "life": 1.2, "size": size})

    def draw_text_shadow(self, x, y, text, fill, font, shadow_color="#000", offset=2, anchor="center", justify="center", wrap_width=None):
        if wrap_width:
            self.canvas.create_text(x + offset, y + offset, text=text, fill=shadow_color, font=font, anchor=anchor, justify=justify, width=wrap_width)
            self.canvas.create_text(x, y, text=text, fill=fill, font=font, anchor=anchor, justify=justify, width=wrap_width)
        else:
            self.canvas.create_text(x + offset, y + offset, text=text, fill=shadow_color, font=font, anchor=anchor, justify=justify)
            self.canvas.create_text(x, y, text=text, fill=fill, font=font, anchor=anchor, justify=justify)

    def main_loop(self):
        if not self.loop_running: return

        now = time.time()
        dt = FPS_DELAY / 1000.0
        self.canvas.delete("all")

        if self.gif_frames and self.state in ["MENU", "ABOUT"]:
            self.gif_timer += dt
            if self.gif_timer >= 0.08:
                self.gif_index = (self.gif_index + 1) % len(self.gif_frames)
                self.gif_timer = 0.0
        
        if self.splash_frames and self.state == "SPLASH":
            self.splash_timer += dt
            if self.splash_timer >= 0.1:
                self.splash_index = (self.splash_index + 1) % len(self.splash_frames)
                self.splash_timer = 0.0

        if getattr(self, 'flash_timer', 0) > 0:
            self.canvas.config(bg="#f0f0f0")
            self.flash_timer -= dt
        else:
            self.canvas.config(bg="#050508")

        sx, sy = 0, 0
        if self.shake_frames > 0:
            progress = self.shake_frames / self.max_shake_frames
            current_intensity = self.shake_intensity * progress
            sx = math.sin(now * 50) * current_intensity
            sy = math.cos(now * 45) * current_intensity
            self.shake_frames -= 1

        if self.state == "SPLASH":
            self.draw_splash(now, sx, sy)
            self.update_animations(dt)
            
        elif self.state == "MENU":
            self.draw_menu(now, sx, sy)
            self.update_animations(dt)
            
        elif self.state == "ABOUT":
            self.draw_about(now, sx, sy)
            self.update_animations(dt)
        
        elif self.state == "PLAYING":
            self.draw_dynamic_bg(now, sx, sy)
            self.update_playing(now)
            self.draw_all(now, sx, sy)
            self.draw_evolution_banner(now, sx, sy)
            self.update_animations(dt)
            
        elif self.state == "PAUSED":
            self.draw_dynamic_bg(now, sx, sy)
            self.draw_all(now, sx, sy)
            self.draw_popup_box("PAUSED", "#1e90ff", "", "pause_pop", "[ P ] RESUME", now, sx, sy)
            
        elif self.state == "GAMEOVER":
            self.draw_dynamic_bg(now, sx, sy)
            self.draw_all(now, sx, sy)
            self.draw_popup_box("STAGE FAILED", "#dc143c", f"FINAL SCORE: {self.score}", "gameover_pop", "[ 1 / 2 ] RESTART", now, sx, sy)
            self.update_animations(dt)
            
        elif self.state == "WIN":
            self.draw_dynamic_bg(now, sx, sy)
            self.draw_all(now, sx, sy)
            self.draw_popup_box("STAGE CLEARED!", "#00ffff", f"LEGENDARY ABO: {self.score}", "win_pop", "[ 1 / 2 ] REPLAY", now, sx, sy)
            self.update_animations(dt)
            
        elif self.state == "EXIT_CONFIRM":
            self.draw_exit_confirm(now, sx, sy)
            self.update_animations(dt)

        self.root.after(FPS_DELAY, self.main_loop)

    def update_playing(self, now):
        if self.evolution_anim_timer > 0:
            self.evolution_anim_timer -= (FPS_DELAY / 1000.0)

        if self.game_mode == "LEVEL" and self.score >= TARGET_SCORE:
            self.state = "WIN"
            self.trigger_shake(15, 5)
            for _ in range(5):
                self.spawn_particles(random.randint(0, WIDTH), random.randint(0, HEIGHT), "#00ffff", 20, burst=True)
            return

        time_since_eat = now - self.last_eat_time
        if time_since_eat > DECAY_TIME and len(self.snake) > 3:
            if not self.decay_active:
                self.decay_active = True
                self.add_floating_text(self.snake[0][0]*CELL, self.snake[0][1]*CELL, "⚠ HUNGER! ⚠", "#ff1493", 20)
            
            if int(time_since_eat * 10) % 10 == 0:
                tail = self.snake.pop()
                self.spawn_particles(tail[0] * CELL + CELL // 2, tail[1] * CELL + CELL // 2, "#666", 3)
        else:
            self.decay_active = False

        if now < self.stun_until: return

        if (now - self.last_move_time) * 1000 >= MOVE_DELAY:
            self.last_move_time = now
            self.direction = self.next_direction
            hx, hy = self.snake[0]
            dx, dy = self.direction
            new_head = (hx + dx, hy + dy)

            if new_head[0] < 0 or new_head[0] >= COLS or new_head[1] < 2 or new_head[1] >= ROWS:
                self.stun_until = now + STUN_DURATION
                loss = max(1, len(self.snake) // 5)
                for _ in range(loss):
                    if len(self.snake) > 3:
                        tail = self.snake.pop()
                        self.spawn_particles(tail[0] * CELL + CELL // 2, tail[1] * CELL + CELL // 2, "#ff6666", 5)
                self.add_floating_text(hx * CELL, hy * CELL, f"-{loss} CREW!", "#dc143c", 16)
                self.trigger_shake(8, 3) 
                self.flash_timer = 0.1
                return

            if new_head in self.obstacles:
                self.obstacles.remove(new_head)
                self.stun_until = now + STUN_DURATION
                self.score = max(0, self.score - 15)
                loss = 2
                for _ in range(loss):
                    if len(self.snake) > 3:
                        tail = self.snake.pop()
                        self.spawn_particles(tail[0] * CELL + CELL // 2, tail[1] * CELL + CELL // 2, "#ff6666", 4)
                
                self.trigger_shake(10, 3)
                self.flash_timer = 0.1
                self.add_floating_text(hx * CELL, hy * CELL - 10, "BAD VIBE! -15", "#dc143c", 16)
                self.spawn_particles(hx * CELL + CELL//2, hy * CELL + CELL//2, "#ff1493", 12, burst=False)
                self.check_evolution()
                return

            if new_head in self.snake[:-1]:
                self.state = "GAMEOVER"
                self.trigger_shake(12, 4)
                self.spawn_particles(hx * CELL, hy * CELL, "#dc143c", 25, burst=False)
                return

            self.snake.insert(0, new_head)

            if new_head == self.food:
                mult = self.stage_index + 1
                self.score += 10 * mult
                self.last_eat_time = now
                self.decay_active = False
                
                stage = EVOLUTION_STAGES[self.stage_index]
                self.spawn_particles(new_head[0] * CELL + CELL//2, new_head[1] * CELL + CELL//2, stage["head"], 10)
                self.add_floating_text(new_head[0] * CELL, new_head[1] * CELL - 15, f"+{10 * mult}", stage["head"], 14)
                self.trigger_shake(4, 2)
                
                self.check_evolution()
                self.spawn_food()
                self.spawn_obstacles()
            else:
                self.snake.pop()

    def update_animations(self, dt):
        for p in self.particles[:]:
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= 0.92
            p["vy"] *= 0.92
            p["life"] -= dt * 1.5
            if p["life"] <= 0:
                self.particles.remove(p)

        for ft in self.floating_texts[:]:
            ft["y"] -= 15 * dt
            ft["life"] -= dt
            if ft["life"] <= 0:
                self.floating_texts.remove(ft)
                
        for n in self.bg_notes:
            n["y"] -= n["speed"]
            if n["y"] < 40:
                n["y"] = HEIGHT + 20
                n["x"] = random.randint(0, WIDTH)

    def draw_dynamic_bg(self, now, sx, sy):
        stage = EVOLUTION_STAGES[self.stage_index]
        bg_accent = stage["bg_accent"]
        
        pulse = math.sin(now * 2) * 15
        self.canvas.create_oval(-50 + sx, -50 + sy, 150 + pulse + sx, 150 + pulse + sy, fill="", outline=bg_accent, width=4)
        self.canvas.create_oval(WIDTH - 150 - pulse + sx, -50 + sy, WIDTH + 50 + sx, 150 + pulse + sy, fill="", outline=bg_accent, width=4)

        for n in self.bg_notes:
            self.canvas.create_text(n["x"] + sx * 0.1, n["y"] + sy * 0.1, text=n["char"], fill="#151a2a", font=("Arial", n["size"]))
        
        bar_w = WIDTH // 30
        for i in range(30):
            wave = math.sin(now * 3 + i * 0.6) * 12 + 18
            bx, by = i * bar_w, HEIGHT - wave
            self.canvas.create_rectangle(bx + sx, by + sy, bx + bar_w - 1 + sx, HEIGHT + sy, fill="#0a0a14", outline="")

    def draw_splash(self, now, sx, sy):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#030305", outline="")
        
        for i in range(0, HEIGHT, 50):
            self.canvas.create_line(0, i, WIDTH, i, fill="#0a0a14")
        for j in range(0, WIDTH, 50):
            self.canvas.create_line(j, 0, j, HEIGHT, fill="#0a0a14")

        mx, my = WIDTH // 2 + sx, HEIGHT // 2 + sy
        hover_y = math.sin(now * 2) * 5
        
        self.draw_text_shadow(mx, my - 180 + hover_y, "ADO'S APPETITE: BLUE ROSE HUNT", "#00ffff", ("Impact", 48, "italic"), "#004444", 4)

        box_size = 220
        gif_y = my + hover_y
        
        self.canvas.create_rectangle(mx - box_size//2 - 12, gif_y - box_size//2 - 12, 
                                     mx + box_size//2 + 12, gif_y + box_size//2 + 12, 
                                     fill="#0a0b12", outline="#1e90ff", width=3)
        self.canvas.create_rectangle(mx - box_size//2, gif_y - box_size//2, 
                                     mx + box_size//2, gif_y + box_size//2, 
                                     fill="#ffffff", outline="")

        cw = 25
        self.canvas.create_line(mx - box_size//2 - 12, gif_y - box_size//2 - 12 + cw, mx - box_size//2 - 12, gif_y - box_size//2 - 12, mx - box_size//2 - 12 + cw, gif_y - box_size//2 - 12, fill="#00ffff", width=4)
        self.canvas.create_line(mx + box_size//2 + 12 - cw, gif_y - box_size//2 - 12, mx + box_size//2 + 12, gif_y - box_size//2 - 12, mx + box_size//2 + 12, gif_y - box_size//2 - 12 + cw, fill="#00ffff", width=4)
        self.canvas.create_line(mx - box_size//2 - 12, gif_y + box_size//2 + 12 - cw, mx - box_size//2 - 12, gif_y + box_size//2 + 12, mx - box_size//2 - 12 + cw, gif_y + box_size//2 + 12, fill="#00ffff", width=4)
        self.canvas.create_line(mx + box_size//2 + 12 - cw, gif_y + box_size//2 + 12, mx + box_size//2 + 12, gif_y + box_size//2 + 12, mx + box_size//2 + 12, gif_y + box_size//2 + 12 - cw, fill="#00ffff", width=4)

        if hasattr(self, 'splash_frames') and self.splash_frames:
            idx = int(now * 15) % len(self.splash_frames)
            self.canvas.create_image(mx, gif_y, image=self.splash_frames[idx])
        else:
            self.draw_text_shadow(mx, gif_y, "[ GIF MISSING ]", "#ff1493", ("Consolas", 14, "bold"))

        btn_y = my + 190 + hover_y
        blink = ">>" if int(now * 3) % 2 == 0 else "  "
        
        self.canvas.create_rectangle(mx - 260, btn_y - 25, mx + 260, btn_y + 25, fill="#030305", outline="#ff1493", width=2)
        self.canvas.create_line(mx - 250, btn_y + 15, mx - 250, btn_y + 25, mx - 240, btn_y + 25, fill="#00ffff", width=2)
        self.canvas.create_line(mx + 250, btn_y - 15, mx + 250, btn_y - 25, mx + 240, btn_y - 25, fill="#00ffff", width=2)

        self.draw_text_shadow(mx, btn_y, f"{blink} ENTER {blink}", "#ffffff", ("Consolas", 16, "bold"))
    
    def draw_menu(self, now, sx, sy):
        if self.gif_frames:
            self.canvas.create_image(WIDTH//2 + sx, HEIGHT//2 + sy, image=self.gif_frames[self.gif_index])
        
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000", stipple="gray25", outline="")
        
        mx, my = WIDTH // 2 + sx, HEIGHT // 2 + sy
        hover_y = math.sin(now * 2) * 8
        
        title_y = my - 140 + hover_y
        
        self.draw_text_shadow(mx, title_y, "ADO'S APPETITE: BLUE ROSE HUNT", 
                             "#38bdf8", ("Impact", 48, "italic"), "#0c4a6e", 4)
        
        self.draw_text_shadow(mx, title_y + 50, "Collect Blue Roses • Avoid Flying Onions", 
                             "#94a3b8", ("Consolas", 14), "#000", 2)
        
        self.canvas.create_line(mx - 200, title_y + 75, mx + 200, title_y + 75, 
                               fill="#38bdf8", width=2)
        
        menu_y = my + 10 + hover_y
        spacing = 55
        
        cursor = "▶" if int(now * 3) % 2 == 0 else " "
        
        menu_items = [
            ("[1] LEVEL MODE", f"Target: {TARGET_SCORE}", "#4ade80"),
            ("[2] ENDLESS MODE", "Survival", "#ec4899"),
            ("[3] ABOUT", "Credits", "#38bdf8"),
            ("[4] EXIT", "Close Game", "#f87171")
        ]
        
        for i, (label, desc, color) in enumerate(menu_items):
            item_y = menu_y + i * spacing
            is_selected = (i == self.menu_selection)
            
            if is_selected:
                self.canvas.create_rectangle(
                    mx - 250, item_y - 20, mx + 250, item_y + 20,
                    fill="#1e293b", outline=color, width=2
                )
            
            label_text = f"{cursor} {label}" if is_selected else f"    {label}"
            self.draw_text_shadow(mx - 230, item_y, label_text, 
                                 color, ("Consolas", 20, "bold"), "#000", 2, anchor="w")
            
            self.draw_text_shadow(mx + 230, item_y, desc, 
                                 "#64748b", ("Consolas", 16), "#000", 1, anchor="e")
        
        footer_y = my + 240 + hover_y
        
        blink = "●" if int(now * 2) % 2 == 0 else "○"
        self.draw_text_shadow(mx, footer_y, f"{blink} USE ARROW KEYS OR PRESS 1-4 {blink}", 
                             "#94a3b8", ("Consolas", 13, "bold"), "#000", 2)

    def draw_exit_confirm(self, now, sx, sy):
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000", stipple="gray75")
        
        mx, my = WIDTH//2 + sx, HEIGHT//2 + sy
        
        box_w, box_h = 600, 500
        box_top = my - box_h//2
        box_bottom = my + box_h//2
        box_left = mx - box_w//2
        box_right = mx + box_w//2
        
        self.canvas.create_rectangle(box_left - 8, box_top - 8, box_right + 8, box_bottom + 8,
                                    fill="#020205", outline="")
        
        self.canvas.create_rectangle(box_left, box_top, box_right, box_bottom,
                                    fill="#0a0b12", outline="#f87171", width=4)
        
        self.canvas.create_rectangle(box_left + 6, box_top + 6, box_right - 6, box_bottom - 6,
                                    fill="", outline="#fff", width=1)
        
        if self.assets.get('exit_pop'):
            self.canvas.create_image(mx, my - 80, image=self.assets['exit_pop'])
        
        self.draw_text_shadow(mx, my + 80, "ARE YOU SURE?", 
                             "#f87171", ("Arial", 36, "bold"), "#000", 3)
        
        self.draw_text_shadow(mx, my + 120, "Do you really want to exit?", 
                             "#e2e8f0", ("Consolas", 16))
        
        btn_y = my + 170
        spacing = 70
        
        self.canvas.create_rectangle(mx - 200, btn_y - 20, mx - 50, btn_y + 20,
                                    fill="#1e293b", outline="#f87171", width=2)
        self.draw_text_shadow(mx - 125, btn_y, "[1] YES, EXIT", 
                             "#f87171", ("Consolas", 16, "bold"))
        
        self.canvas.create_rectangle(mx + 50, btn_y - 20, mx + 200, btn_y + 20,
                                    fill="#1e293b", outline="#4ade80", width=2)
        self.draw_text_shadow(mx + 125, btn_y, "[2] NO, STAY", 
                             "#4ade80", ("Consolas", 16, "bold"))
        
        self.draw_text_shadow(mx, box_bottom - 30, "Press 1/Y to exit or 2/N to stay", 
                             "#64748b", ("Consolas", 11))

    def draw_about(self, now, sx, sy):
        if self.gif_frames:
            self.canvas.create_image(WIDTH//2 + sx, HEIGHT//2 + sy, image=self.gif_frames[self.gif_index])
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000", stipple="gray75")
        
        mx, my = WIDTH//2 + sx, HEIGHT//2 + sy
        hover_y = math.sin(now * 1.5) * 4
        
        box_w, box_h = 1050, 520
        box_top = my - box_h//2
        box_bottom = my + box_h//2
        box_left = mx - box_w//2
        box_right = mx + box_w//2
        
        border_color = "#3a7ca5"
        accent_color = "#5bc0be"
        pink_color   = "#c75b8a"
        bg_box       = "#0a0b12"
        bg_header    = "#20344d"
        
        self.canvas.create_rectangle(box_left, box_top, box_right, box_bottom, fill=bg_box, outline=border_color, width=3)
        self.canvas.create_rectangle(box_left - 5, box_top - 5, box_right + 5, box_bottom + 5, fill="", outline=accent_color, width=1)
        
        self.canvas.create_rectangle(box_left, box_top, box_right, box_top + 50, fill=bg_header, outline="")
        self.draw_text_shadow(mx, box_top + 25, "A B O U T   M E", "#f0f0f0", ("Consolas", 22, "bold"))

        img_x = box_left + 220
        img_y = my - 10 + hover_y

        if self.assets.get('hitori_ado'):
            if 'hitori_ado_about' not in self.assets:
                try:
                    hitori_png = resource_path("assets/HitorixAdo.png")
                    hitori_jpg = resource_path("assets/HitorixAdo.jpg")
                    hitori_path = hitori_png if os.path.exists(hitori_png) else hitori_jpg
                    if os.path.exists(hitori_path):
                        img = Image.open(hitori_path).convert("RGBA")
                        img = img.resize((240, 240), Image.Resampling.LANCZOS)
                        self.assets['hitori_ado_about'] = ImageTk.PhotoImage(img)
                except:
                    pass
            
            about_img = self.assets.get('hitori_ado_about')
            if about_img:
                self.canvas.create_image(img_x, img_y, image=about_img)
                self.canvas.create_rectangle(img_x - 122, img_y - 122, img_x + 122, img_y + 122, outline=pink_color, width=3)
                self.canvas.create_rectangle(img_x - 130, img_y - 130, img_x - 90, img_y - 130, outline=accent_color, width=4) 
                self.canvas.create_rectangle(img_x + 90, img_y + 130, img_x + 130, img_y + 130, outline=accent_color, width=4) 

        self.draw_text_shadow(img_x, img_y + 160, "ID: STEVEN", accent_color, ("Consolas", 18, "bold"))
        self.draw_text_shadow(img_x, img_y + 190, "LOC: INDONESIA", border_color, ("Consolas", 14, "bold"))

        text_x = box_left + 440
        text_y = box_top + 90
        max_text_width = 560

        p1 = ("Hey! I'm Steven, a math student.\n"
              "This is my Final Project for Stanford University's program.")
        self.draw_text_shadow(text_x, text_y, p1, "#e8e8e8", ("Consolas", 14),
                              anchor="nw", justify="left", wrap_width=max_text_width)

        p2 = ("I originally planned to keep this project simple and "
              "follow exactly what was taught in class. That plan lasted "
              "for about five minutes. Somewhere along the way I started "
              "adding extra features, experimenting with new ideas, and "
              "writing code I probably wasn't supposed to know yet.")
        self.draw_text_shadow(text_x, text_y + 70, p2, "#8ab4f8", ("Consolas", 12),
                              anchor="nw", justify="left", wrap_width=max_text_width)

        p3 = ("As a huge Ado fan, I wanted the project to feel a little "
              "more personal instead of looking like another generic "
              "assignment. Between university work, and way too much music"
              " this ended up becoming something I genuinely enjoyed building.")
        self.draw_text_shadow(text_x, text_y + 175, p3, "#d5a6bd", ("Consolas", 12),
                              anchor="nw", justify="left", wrap_width=max_text_width)

        p4 = ("DISCLAIMER: I do NOT own any images or assets used here. "
              "They belong to their respective creators and are used "
              "purely for educational purposes.\n\n"
              "Please don't sue me. I just want to graduate, listen to Ado"
              " and continue pretending I understand all of my code.")
        self.draw_text_shadow(text_x, text_y + 260, p4, "#999999",
                              ("Consolas", 12, "italic"), anchor="nw",
                              justify="left", wrap_width=max_text_width)

        if int(now * 2.5) % 2 == 0:
            self.draw_text_shadow(mx, box_bottom - 30, 
                                 "[ M ] BACK TO MENU", 
                                 accent_color, ("Consolas", 18, "bold"))

    def draw_popup_box(self, title, border_color, score_text, img_key, resume_text, now, sx, sy):
        mx, my = WIDTH//2 + sx, HEIGHT//2 + sy
        self.canvas.create_rectangle(0, 0, WIDTH, HEIGHT, fill="#000", stipple="gray50")
        
        box_w, box_h = 500, 520
        self.canvas.create_rectangle(mx - box_w//2 - 8, my - box_h//2 - 8, mx + box_w//2 + 8, my + box_h//2 + 8, fill="#020205", outline="")
        self.canvas.create_rectangle(mx - box_w//2, my - box_h//2, mx + box_w//2, my + box_h//2, fill="#0a0a14", outline=border_color, width=4)
        self.canvas.create_rectangle(mx - box_w//2 + 6, my - box_h//2 + 6, mx + box_w//2 - 6, my + box_h//2 - 6, fill="", outline="#fff", width=1)
        
        img = self.assets.get(img_key)
        if img:
            self.canvas.create_image(mx, my - 80, image=img)
            
        self.draw_text_shadow(mx, my + 100, title, border_color, ("Arial", 38, "bold"), "#000", 2, wrap_width=450)
        if score_text:
            self.draw_text_shadow(mx, my + 150, score_text, "#fff", ("Consolas", 20, "bold"), wrap_width=450)
            
        if int(now * 2) % 2 == 0:
            self.draw_text_shadow(mx, my + 200, resume_text, border_color, ("Consolas", 18, "bold"))
        self.draw_text_shadow(mx, my + 240, "[ M ] BACK TO MENU", "#aaa", ("Consolas", 14, "bold"))

    def draw_evolution_banner(self, now, sx, sy):
        if self.evolution_anim_timer > 0:
            stage = EVOLUTION_STAGES[self.stage_index]
            mx, my = WIDTH // 2 + sx, HEIGHT // 2 + sy
            y_offset = (2.0 - self.evolution_anim_timer) * 30
            
            self.canvas.create_rectangle(0, my - 60 - y_offset, WIDTH, my + 60 - y_offset, fill="#000", stipple="gray50", outline="")
            self.draw_text_shadow(mx, my - y_offset, f"ERA UNLOCKED: {stage['name']}", stage["head"], ("Arial", 42, "bold", "italic"))
            self.draw_text_shadow(mx, my + 35 - y_offset, stage["msg"], "#fff", ("Consolas", 16))

    def draw_all(self, now, sx, sy):
        self.draw_food(now, sx, sy)
        self.draw_obstacles(now, sx, sy)
        self.draw_snake_entourage(sx, sy)
        self.draw_particles(sx, sy)
        self.draw_floating_texts(sx, sy)
        self.draw_hud(now, sx, sy)

    def draw_obstacles(self, now, sx, sy):
        pulse = math.sin(now * 6) * 1.5
        for ox, oy in self.obstacles:
            cx, cy = ox * CELL + CELL // 2 + sx, oy * CELL + CELL // 2 + sy
            
            if self.assets.get('flying_onion'):
                bob_y = cy + math.sin(now * 8 + ox) * 3
                self.canvas.create_image(cx, bob_y, image=self.assets['flying_onion'])
            else:
                s = 12 + pulse
                self.canvas.create_line(cx - s, cy - s, cx + s, cy + s, fill="#dc143c", width=4, capstyle=tk.ROUND)
                self.canvas.create_line(cx - s, cy + s, cx + s, cy - s, fill="#dc143c", width=4, capstyle=tk.ROUND)

    def draw_snake_entourage(self, sx, sy):
        stage = EVOLUTION_STAGES[self.stage_index]
        is_legendary = stage["name"] == "Legendary Abo"
        
        if len(self.snake) > 1:
            pts = [(x * CELL + CELL//2 + sx, y * CELL + CELL//2 + sy) for x, y in self.snake]
            self.canvas.create_line(pts, fill=stage["glow"], width=12, capstyle=tk.ROUND, joinstyle=tk.ROUND)

        for i, (x, y) in enumerate(self.snake):
            cx, cy = x * CELL + CELL // 2 + sx, y * CELL + CELL // 2 + sy
            if i == 0:
                head_img = self.assets.get('head_legend') if is_legendary else self.assets.get('head_chill')
                if head_img:
                    self.canvas.create_image(cx, cy, image=head_img)
                    self.canvas.create_oval(cx - 28, cy - 28, cx + 28, cy + 28, fill="", outline=stage["head"], width=2)
            else:
                crew_img = self.assets.get('crew_legend') if is_legendary else self.assets.get('crew_chill')
                if crew_img:
                    self.canvas.create_image(cx, cy, image=crew_img)

    def draw_food(self, now, sx, sy):
        if not self.food: return
        fx, fy = self.food
        cx, cy = fx * CELL + CELL // 2 + sx, fy * CELL + CELL // 2 + sy
        
        if self.assets.get('food_rose'):
            pulse = math.sin(now * 8) * 3 
            self.canvas.create_image(cx, cy + pulse, image=self.assets['food_rose'])
        else:
            self.canvas.create_oval(cx - 14, cy - 14, cx + 14, cy + 14, fill="#1e90ff", outline="#fff")

    def draw_particles(self, sx, sy):
        for p in self.particles:
            if p["life"] > 0:
                px, py = p["x"] + sx, p["y"] + sy
                self.canvas.create_rectangle(px - p["size"]/2, py - p["size"]/2, px + p["size"]/2, py + p["size"]/2, fill=p["color"], outline="")

    def draw_floating_texts(self, sx, sy):
        for ft in self.floating_texts:
            self.draw_text_shadow(ft["x"] + sx, ft["y"] + sy, ft["text"], ft["color"], ("Arial", ft["size"], "bold"))

    def draw_hud(self, now, sx, sy):
        stage = EVOLUTION_STAGES[self.stage_index]
        header_height = CELL * 2
        
        self.canvas.create_rectangle(0, 0, WIDTH, header_height, fill="#050508", outline="")
        self.canvas.create_line(0, header_height, WIDTH, header_height, fill=stage["head"], width=3)
        
        mode_text = f"MODE: {self.game_mode}"
        target_text = f" / TARGET: {TARGET_SCORE}" if self.game_mode == "LEVEL" else ""
        
        self.draw_text_shadow(20, 16, f"SCORE: {self.score}", "#fff", ("Consolas", 18, "bold"), anchor="w")
        self.draw_text_shadow(20, 42, f"ERA: {stage['name']}", stage["head"], ("Consolas", 14, "bold"), anchor="w")
        
        self.draw_text_shadow(WIDTH - 20, 16, mode_text + target_text, "#ccc", ("Consolas", 12, "bold"), anchor="e")

        if self.stage_index < len(EVOLUTION_STAGES) - 1:
            prev = stage["threshold"]
            nxt = EVOLUTION_STAGES[self.stage_index + 1]["threshold"]
            progress = min(1.0, (self.score - prev) / max(1, nxt - prev))
            
            bar_w = 300
            bar_x = WIDTH // 2 - bar_w // 2
            self.canvas.create_rectangle(bar_x, 30, bar_x + bar_w, 42, fill="#111", outline="#333", width=2)
            self.canvas.create_rectangle(bar_x, 30, bar_x + (bar_w * progress), 42, fill=stage["head"], outline="")
            self.draw_text_shadow(WIDTH // 2, 18, "NEXT ERA", "#aaa", ("Arial", 10, "bold"))

        elapsed = now - getattr(self, 'last_eat_time', now)
        if elapsed > DECAY_TIME * 0.6:
            if int(now * 4) % 2 == 0:
                self.draw_text_shadow(WIDTH - 20, 42, "⚠ LOW HYPE ⚠", "#ff1493", ("Consolas", 16, "bold"), anchor="e")
                self.canvas.create_rectangle(2, header_height + 2, WIDTH-2, HEIGHT-2, outline="#ff1493", width=4)

if __name__ == "__main__":
    root = tk.Tk()
    root.resizable(False, False)
    root.eval('tk::PlaceWindow . center')
    game = ADOGames(root)
    root.mainloop()