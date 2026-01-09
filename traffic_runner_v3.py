import pygame
import random
import sys
import os
import cv2
import mediapipe as mp

# --- MediaPipe (Yüz Takibi) Kurulumu ---
mp_face_mesh = mp.solutions.face_mesh
face_mesh = mp_face_mesh.FaceMesh(
    max_num_faces=1, 
    refine_landmarks=False, 
    min_detection_confidence=0.5
)
cap = cv2.VideoCapture(0)

# --- Temel Başlatma ---
pygame.init()
GENISLIK, YUKSEKLIK = 600, 800
ekran = pygame.display.set_mode((GENISLIK, YUKSEKLIK))
pygame.display.set_caption("Trafik Kosucusu - Boyun Kontrollü Fren")

# --- Renkler ve Fontlar ---
SIYAH = (30, 30, 30)
BEYAZ = (255, 255, 255)
ALTIN_SARISI = (255, 215, 0)
KIRMIZI = (200, 0, 0)
font = pygame.font.SysFont("Arial", 32, bold=True)

# --- Şerit Ayarları ---
SERIT_SAYISI = 4
serit_genislik = GENISLIK // SERIT_SAYISI
serit_konum = [i * serit_genislik + (serit_genislik // 2) for i in range(SERIT_SAYISI)]

def safe_load(filename, w, h, color):
    try:
        path = os.path.join(os.path.dirname(__file__), filename)
        if os.path.exists(path):
            img = pygame.image.load(path).convert_alpha()
            return pygame.transform.scale(img, (w, h))
    except: pass
    surf = pygame.Surface((w, h))
    surf.fill(color)
    return surf

PLAYER_IMG = safe_load('player_car.png', 50, 90, (0, 255, 0))
COIN_IMG = safe_load('coin.png', 35, 35, ALTIN_SARISI)
ENEMY_LIST = [safe_load('enemy_car_red.png', 50, 90, (200, 0, 0))]

def main():
    clock = pygame.time.Clock()
    oyuncu_x = serit_konum[1]
    hedef_x = oyuncu_x
    aktif_serit = 1
    
    nesneler = []
    yol_ofset = 0
    normal_hiz = 14
    fren_hizi = 4
    yol_hizi = normal_hiz
    
    skor = 0
    oyun_aktif = True
    
    ref_y = None # Kalibrasyon için başlangıç burun yüksekliği

    while True:
        # 1. Kamera Görüntüsünü İşle
        ret, frame = cap.read()
        fren_yapiliyor = False
        
        if ret:
            frame = cv2.flip(frame, 1)
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = face_mesh.process(rgb_frame)
            
            if results.multi_face_landmarks:
                # Burun ucu koordinatını al (Y ekseni)
                burun_y = results.multi_face_landmarks[0].landmark[4].y
                
                # İlk karede burun konumunu referans al
                if ref_y is None:
                    ref_y = burun_y
                
                # Eğer burun referanstan belli bir eşik kadar aşağıdaysa fren yap
                if burun_y > ref_y + 0.07: 
                    fren_yapiliyor = True

        # 2. Hız Kontrolü
        hedef_v = fren_hizi if fren_yapiliyor else normal_hiz
        yol_hizi += (hedef_v - yol_hizi) * 0.1 # Yumuşak geçiş

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                cap.release()
                pygame.quit(); sys.exit()
            
            if event.type == pygame.KEYDOWN:
                if oyun_aktif:
                    if event.key == pygame.K_LEFT and aktif_serit > 0:
                        aktif_serit -= 1
                    if event.key == pygame.K_RIGHT and aktif_serit < SERIT_SAYISI - 1:
                        aktif_serit += 1
                    hedef_x = serit_konum[aktif_serit]
                else:
                    if event.key == pygame.K_RETURN:
                        main()

        if oyun_aktif:
            oyuncu_x += (hedef_x - oyuncu_x) * 0.2
            oyuncu_rect = PLAYER_IMG.get_rect(center=(int(oyuncu_x), YUKSEKLIK - 120))
            yol_ofset = (yol_ofset + yol_hizi) % 80
            
            if random.random() < 0.025: 
                tip = "altin" if random.random() < 0.3 else "araba"
                img = COIN_IMG if tip == "altin" else random.choice(ENEMY_LIST)
                rect = img.get_rect(center=(random.choice(serit_konum), -100))
                nesneler.append([rect, 1.0 if tip == "altin" else 0.5, tip, img])

            ekran.fill(SIYAH)
            
            for i in range(1, SERIT_SAYISI):
                x_c = i * serit_genislik
                for y_c in range(-80, YUKSEKLIK + 80, 80):
                    pygame.draw.rect(ekran, BEYAZ, (x_c - 2, int(y_c + yol_ofset), 4, 40))

            for n in nesneler[:]:
                n[0].y += yol_hizi * n[1]
                ekran.blit(n[3], n[0])
                if oyuncu_rect.colliderect(n[0]):
                    if n[2] == "altin":
                        skor += 10
                        nesneler.remove(n)
                    else: oyun_aktif = False 
                elif n[0].y > YUKSEKLIK: nesneler.remove(n)

            ekran.blit(PLAYER_IMG, oyuncu_rect)
            
            # Fren Bildirimi ve Skor
            if fren_yapiliyor:
                ekran.blit(font.render("FREN", True, KIRMIZI), (GENISLIK//2-40, 50))
            ekran.blit(font.render(f"Puan: {skor}", True, ALTIN_SARISI), (20, 20))
            normal_hiz += 0.0004 
        else:
            overlay = pygame.Surface((GENISLIK, YUKSEKLIK), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 150))
            ekran.blit(overlay, (0,0))
            ekran.blit(font.render("KAZA!", True, KIRMIZI), (GENISLIK//2-50, 350))

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main()