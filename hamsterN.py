import pygame
import sys
import os
import random

# --- resource_path Funktion ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# --- Hilfsfunktion zum Laden von Animationsframes ---
def load_animation_frames(folder_path, base_filename_prefix, num_frames, target_height):
    frames = []
    for i in range(num_frames):
        filename = f"{base_filename_prefix}{i:03d}.png"
        img_path = resource_path(os.path.join(folder_path, filename))
        try:
            img = pygame.image.load(img_path).convert_alpha()
            img = scale_image_height(img, target_height)
            frames.append(img)
        except pygame.error as e:
            print(f"Fehler beim Laden von Frame: {img_path} - {e}")
            continue
        except FileNotFoundError:
            print(f"Datei nicht gefunden: {img_path}")
            continue
    if not frames:
        print(f"WARNUNG: Keine Frames für '{base_filename_prefix}' in '{folder_path}' geladen.")
    return frames

# --- Hilfsfunktion zum Skalieren ---
def scale_image_height(image, target_height):
    if image.get_height() == 0: return image
    ratio = target_height / image.get_height()
    return pygame.transform.smoothscale(image, (int(image.get_width() * ratio), target_height))

# 1. Pygame initialisieren
pygame.init()

# 2. Fenster-Dimensionen & Titel
SCREEN_WIDTH = 360
SCREEN_HEIGHT = 240
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("HamsterN!")
pygame.display.set_icon(pygame.image.load(resource_path(os.path.join('assets', 'HamsterN_ICON.ico'))))

# 3. Farben
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
RED = (255, 0, 0)
SEMI_TRANSPARENT_WHITE = (255, 255, 255, 128) # Weiß mit 50% Alpha (128 von 255)
BUTTON_COLOR = (100, 100, 200)
BUTTON_TEXT_COLOR = WHITE

# 4. Bilder laden
try:
    ASSETS_BASE_FOLDER = 'assets'
    BACKGROUND_FOLDER = os.path.join(ASSETS_BASE_FOLDER, 'background')
    CHAR_FOLDER = os.path.join(ASSETS_BASE_FOLDER, 'char', 'indi')

    background_filename = 'bg_indi.png' # Passe dies an dein Bild an!
    background_img_path = resource_path(os.path.join(BACKGROUND_FOLDER, background_filename))
    background_img = pygame.image.load(background_img_path).convert()
    background_img = pygame.transform.scale(background_img, (SCREEN_WIDTH, SCREEN_HEIGHT))

    TARGET_CHAR_HEIGHT = 70
    char_idle_imgs = load_animation_frames(CHAR_FOLDER, 'Idle__', 10, TARGET_CHAR_HEIGHT)
    char_run_imgs = load_animation_frames(CHAR_FOLDER, 'Run__', 10, TARGET_CHAR_HEIGHT)
    char_sleep_imgs = load_animation_frames(CHAR_FOLDER, 'Dead__', 10, TARGET_CHAR_HEIGHT)

    if not char_idle_imgs or not char_run_imgs or not char_sleep_imgs:
        print("Fehler: Nicht alle Charakteranimationen konnten geladen werden.")
        pygame.quit(); sys.exit()
except Exception as e: # Allgemeinere Exception für den Fall der Fälle
    print(f"Fehler beim Laden der Bilder: {e}")
    pygame.quit(); sys.exit()

# 5. Spiel-Variablen
running = True
clock = pygame.time.Clock()
game_over = False # NEU: Spielzustand

# --- Funktion zum Zurücksetzen des Spiels ---
def reset_game_state():
    global activity_level, energy, score, is_sleeping, time_char_stopped, game_over
    global idle_anim_index, run_anim_index, sleep_anim_index, last_activity_time, last_animation_update
    
    activity_level = 0
    energy = MAX_ENERGY # Start mit voller Energie
    score = 0 # Score wird nicht zurückgesetzt, wenn man nur den Charakter wiederbelebt
              # Wenn du den Score auch resetten willst: score = 0
    is_sleeping = False
    time_char_stopped = 0
    game_over = False

    idle_anim_index = 0
    run_anim_index = 0
    sleep_anim_index = 0 # Wird auf den letzten Frame gesetzt, wenn game_over erreicht wird
    last_activity_time = pygame.time.get_ticks()
    last_animation_update = pygame.time.get_ticks()
    print("Spiel zurückgesetzt.")


# Animation
idle_anim_index = 0
run_anim_index = 0
sleep_anim_index = 0
last_animation_update = pygame.time.get_ticks()
idle_animation_speed_ms = 150
run_animation_speed_ms = 100
sleep_animation_speed_ms = 150 # Geschwindigkeit der "Todes"-Animation

# Aktivität
activity_level = 0
last_activity_time = pygame.time.get_ticks()
ACTIVITY_DECAY_RATE = 0.1
ACTIVITY_THRESHOLD_FOR_RUNNING = 5

# Energie & Schlaf
energy = 100
MAX_ENERGY = 100
ENERGY_DECAY_WHILE_RUNNING = 0.1 # Energieverlust pro Frame beim Rennen
ENERGY_GAIN_PER_ACTION = 0.5
is_sleeping = False # Dieser Zustand wird jetzt durch game_over abgelöst, wenn Energie 0 ist
time_char_stopped = 0 # Wann der Charakter inaktiv wurde (für Schlaf-Logik vor Energie 0)
# SLEEP_DELAY_MS = 10 * 1000 # Zeit bis zum Einschlafen bei Inaktivität (vor Energie 0) - erstmal auskommentiert, Fokus auf Energie 0

current_char_image = char_idle_imgs[0]
# Charakter-Position angepasst
char_rect = current_char_image.get_rect(centerx=SCREEN_WIDTH // 2, bottom=SCREEN_HEIGHT - 30)

# Highscore
score = 0
highscore = 0
FONT_SIZE = 18
INFO_TEXT_Y_START = 5
INFO_TEXT_LINE_HEIGHT = FONT_SIZE + 2
INFO_TEXT_BOX_PADDING = 5

try:
    game_font = pygame.font.Font(None, FONT_SIZE)
except Exception as e:
    game_font = pygame.font.SysFont("arial", FONT_SIZE)

# "Neu starten"-Button
BUTTON_WIDTH = 150
BUTTON_HEIGHT = 50
restart_button_rect = pygame.Rect(
    (SCREEN_WIDTH - BUTTON_WIDTH) // 2,
    (SCREEN_HEIGHT - BUTTON_HEIGHT) // 2,
    BUTTON_WIDTH,
    BUTTON_HEIGHT
)
button_font = pygame.font.Font(None, 28)


# --- Pfad für Highscore-Datei ---
def get_highscore_file_path():
    app_name = "HamsterN!"
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        if sys.platform == "win32": path = os.path.join(os.environ['APPDATA'], app_name)
        elif sys.platform == "darwin": path = os.path.join(os.path.expanduser("~"), "Library", "Application Support", app_name)
        else: path = os.path.join(os.path.expanduser("~"), ".local", "share", app_name)
    else:
        path = os.path.dirname(os.path.abspath(__file__))
    if not os.path.exists(path):
        try: os.makedirs(path, exist_ok=True)
        except OSError as e: path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(path, "highscore.txt")
HIGHSCORE_FILE = get_highscore_file_path()
print(f"Highscore Datei: {HIGHSCORE_FILE}")
def load_highscore_func():
    try:
        with open(HIGHSCORE_FILE, "r") as f: return int(f.read())
    except (FileNotFoundError, ValueError): return 0
def save_highscore_func(current_score_to_save):
    try:
        with open(HIGHSCORE_FILE, "w") as f: f.write(str(current_score_to_save))
    except IOError as e: print(f"Konnte Highscore nicht speichern: {e}")
highscore = load_highscore_func()


# 6. Haupt-Game-Loop
while running:
    current_time_ticks = pygame.time.get_ticks()
    mouse_pos = pygame.mouse.get_pos()

    # 6.1. Event-Handling
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if game_over:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1: # Linksklick
                if restart_button_rect.collidepoint(mouse_pos):
                    reset_game_state() # Ruft die Reset-Funktion auf
        else: # Nur Events verarbeiten, wenn nicht game_over
            action_detected = False
            # `is_sleeping` wird jetzt durch `game_over` ersetzt für den Zustand "Energie 0"
            if energy > 0: # Aktionen nur möglich, wenn Energie vorhanden ist
                if event.type == pygame.KEYDOWN: activity_level += 2; action_detected = True
                if event.type == pygame.MOUSEBUTTONDOWN: activity_level += 1; action_detected = True
                if event.type == pygame.MOUSEMOTION: activity_level += 0.2; action_detected = True
            
            if action_detected:
                last_activity_time = current_time_ticks
                energy = min(MAX_ENERGY, energy + ENERGY_GAIN_PER_ACTION)
                score += activity_level * 0.1 # Score auch bei game_over weiterlaufen lassen? Eher nicht.
                # is_sleeping und time_char_stopped Logik hier ggf. überdenken, wenn es noch einen "normalen" Schlaf geben soll

    # 6.2. Logik des Spiels (nur wenn nicht game_over)
    if not game_over:
        if current_time_ticks - last_activity_time > 1000 and activity_level > 0: # Jede Sekunde Inaktivität
            activity_level -= ACTIVITY_DECAY_RATE
            last_activity_time = current_time_ticks
        activity_level = max(0, activity_level)

        if activity_level > ACTIVITY_THRESHOLD_FOR_RUNNING and energy > 0:
            energy -= ENERGY_DECAY_WHILE_RUNNING
        energy = max(0, energy)

        if energy <= 0:
            game_over = True
            activity_level = 0 # Stoppe Aktivität, wenn Energie leer
            # Stelle sicher, dass die "Todes"-Animation beim letzten Frame ist, wenn game_over eintritt
            sleep_anim_index = len(char_sleep_imgs) - 1 
            current_char_image = char_sleep_imgs[sleep_anim_index]


    # Charakterbild & Animation aktualisieren
    if game_over:
        # "Todes"-Animation, stoppt beim letzten Frame
        if sleep_anim_index < len(char_sleep_imgs) - 1: # Nur animieren, wenn nicht schon am Ende
             if current_time_ticks - last_animation_update > sleep_animation_speed_ms:
                sleep_anim_index += 1
                last_animation_update = current_time_ticks
        current_char_image = char_sleep_imgs[sleep_anim_index]
    elif activity_level > ACTIVITY_THRESHOLD_FOR_RUNNING and energy > 0: # Charakter rennt
        if current_time_ticks - last_animation_update > run_animation_speed_ms:
            run_anim_index = (run_anim_index + 1) % len(char_run_imgs)
            last_animation_update = current_time_ticks
        current_char_image = char_run_imgs[run_anim_index]
        idle_anim_index = 0; sleep_anim_index = 0 # Reset other anims
    else: # Charakter steht (Idle-Animation) oder hat keine Energie (zeigt dann auch Idle, bevor game_over)
        if current_time_ticks - last_animation_update > idle_animation_speed_ms:
            idle_anim_index = (idle_anim_index + 1) % len(char_idle_imgs)
            last_animation_update = current_time_ticks
        current_char_image = char_idle_imgs[idle_anim_index]
        run_anim_index = 0; sleep_anim_index = 0 # Reset other anims
    
    char_rect = current_char_image.get_rect(centerx=SCREEN_WIDTH // 2, bottom=SCREEN_HEIGHT - 30)


    # 6.3. Bildschirm zeichnen
    screen.blit(background_img, (0,0))
    screen.blit(current_char_image, char_rect)

    # --- Texte mit transparenter Box zeichnen ---
    # Berechne Höhe und Breite der Box basierend auf Anzahl der Textzeilen
    num_text_lines = 3
    text_box_height = (num_text_lines * INFO_TEXT_LINE_HEIGHT) + (INFO_TEXT_BOX_PADDING * 2) - (INFO_TEXT_LINE_HEIGHT - FONT_SIZE) # Etwas Feintuning für Padding
    text_box_width = SCREEN_WIDTH * 0.4 # Ca. 40% der Bildschirmbreite
    text_box_rect = pygame.Rect(INFO_TEXT_BOX_PADDING, INFO_TEXT_BOX_PADDING, text_box_width, text_box_height)

    # Erstelle eine separate Surface für die Transparenz
    transparent_surface = pygame.Surface((text_box_width, text_box_height), pygame.SRCALPHA)
    transparent_surface.fill(SEMI_TRANSPARENT_WHITE) # Fülle mit halbtransparentem Weiß
    screen.blit(transparent_surface, (text_box_rect.x, text_box_rect.y))
    
    # Texte zeichnen
    if score > highscore: highscore = score
    score_surface = game_font.render(f"Score: {int(score)}", True, BLACK)
    highscore_surface = game_font.render(f"Highscore: {int(highscore)}", True, BLACK)
    energy_color = BLACK if energy > 20 else RED
    energy_surface = game_font.render(f"Energie: {int(energy)}%", True, energy_color)
    
    text_x_offset = text_box_rect.x + INFO_TEXT_BOX_PADDING
    screen.blit(score_surface, (text_x_offset, text_box_rect.y + INFO_TEXT_BOX_PADDING))
    screen.blit(highscore_surface, (text_x_offset, text_box_rect.y + INFO_TEXT_BOX_PADDING + INFO_TEXT_LINE_HEIGHT))
    screen.blit(energy_surface, (text_x_offset, text_box_rect.y + INFO_TEXT_BOX_PADDING + INFO_TEXT_LINE_HEIGHT * 2))

    # "Neu starten"-Button zeichnen, wenn game_over
    if game_over:
        pygame.draw.rect(screen, BUTTON_COLOR, restart_button_rect, border_radius=10)
        restart_text_surface = button_font.render("Neu starten", True, BUTTON_TEXT_COLOR)
        restart_text_rect = restart_text_surface.get_rect(center=restart_button_rect.center)
        screen.blit(restart_text_surface, restart_text_rect)
        
        # Optional: "Game Over" Text
        game_over_font = pygame.font.Font(None, 40)
        game_over_surface = game_over_font.render("Game Over!", True, RED)
        game_over_text_rect = game_over_surface.get_rect(centerx=SCREEN_WIDTH // 2, centery=SCREEN_HEIGHT // 2 - 50)
        screen.blit(game_over_surface, game_over_text_rect)


    # 6.4. Alles auf dem Bildschirm anzeigen
    pygame.display.flip()

    # 6.5. Framerate begrenzen
    clock.tick(30)

# 7. Pygame sauber beenden
save_highscore_func(highscore)
pygame.quit()
sys.exit()