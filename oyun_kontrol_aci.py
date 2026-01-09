import cv2
import mediapipe as mp
import numpy as np
import pyautogui
import time

# --- AÇI HESAPLAMA FONKSİYONU ---
def aci_hesapla(a, b, c):
    """Üç 2D nokta (omuz, dirsek, bilek) arasındaki açıyı derece cinsinden hesaplar."""
    a = np.array(a) # Birinci nokta (Omuz)
    b = np.array(b) # İkinci nokta (Dirsek, köşe)
    c = np.array(c) # Üçüncü nokta (Bilek)
    
    # Vektörlerin bulunması
    ba = a - b
    bc = c - b
    
    # Kosinüs teoreminden açı hesaplama (Skaler çarpım / Vektör uzunlukları çarpımı)
    kosinus_acisi = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc))
    
    # Açıya çevirme ve dereceye dönüştürme
    aci = np.arccos(np.clip(kosinus_acisi, -1.0, 1.0)) # Açı 180'in dışında olmasın
    aci = np.degrees(aci)
        
    return aci

# --- MEDIAPIPE VE OPENCV KURULUMU ---
mp_drawing = mp.solutions.drawing_utils
mp_pose = mp.solutions.pose

# --- KONTROL AYARLARI ---
# Kolun katlanmış kabul edilmesi için gerekli maksimum açı (Dirsek açısı)
ACI_ESIGI = 135 # 135 dereceden küçükse kol katlanmıştır (90 derece L şeklidir)
AKTIF_KONTROL_SAYISI = 0 

# --- KAMERA BAŞLATMA ---
cap = cv2.VideoCapture(0) # Genellikle 0 varsayılan kameradır

if not cap.isOpened():
    print("HATA: Kamera açılamadı. İndeksi veya izinleri kontrol edin.")
    exit()

aktif_kontrol = 'NONE'

# --- ANA DÖNGÜ ---
with mp_pose.Pose(min_detection_confidence=0.7, min_tracking_confidence=0.7) as pose:
    while cap.isOpened():
        success, image = cap.read()
        if not success:
            continue

        # Görüntü İşleme
        image = cv2.flip(image, 1) # Ayna etkisi için çevir
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        results = pose.process(image_rgb)
        
        yeni_kontrol = 'NONE'
        
        if results.pose_landmarks:
            landmarks = results.pose_landmarks.landmark
            
            # --- Nokta Koordinatlarını Çekme ---
            try:
                # SOL KOL NOKTALARI
                sol_omuz = [landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.LEFT_SHOULDER].y]
                sol_dirsek = [landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].x, landmarks[mp_pose.PoseLandmark.LEFT_ELBOW].y]
                sol_bilek = [landmarks[mp_pose.PoseLandmark.LEFT_WRIST].x, landmarks[mp_pose.PoseLandmark.LEFT_WRIST].y]
                
                # SAĞ KOL NOKTALARI
                sag_omuz = [landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].x, landmarks[mp_pose.PoseLandmark.RIGHT_SHOULDER].y]
                sag_dirsek = [landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW].x, landmarks[mp_pose.PoseLandmark.RIGHT_ELBOW].y]
                sag_bilek = [landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].x, landmarks[mp_pose.PoseLandmark.RIGHT_WRIST].y]
                
                # --- AÇI HESAPLAMA ---
                sol_aci = aci_hesapla(sol_omuz, sol_dirsek, sol_bilek)
                sag_aci = aci_hesapla(sag_omuz, sag_dirsek, sag_bilek)
                
                # --- AÇI EŞİĞİ KONTROLÜ ---
                # Açı eşiğin altındaysa, kol katlanmış demektir.
                sol_kol_katli = sol_aci < ACI_ESIGI
                sag_kol_katli = sag_aci < ACI_ESIGI
                
                # --- ANA KONTROL MANTIĞI (ÖNCELİK SIRASINA GÖRE) ---
                
                # 1. ZIPLA (İki kol da katlıysa)
                if sol_kol_katli and sag_kol_katli:
                    yeni_kontrol = 'UP'
                
                # 2. SAĞA GİT (Sadece sol kol katlıysa)
                elif sol_kol_katli and not sag_kol_katli:
                    yeni_kontrol = 'RIGHT'
                    
                # 3. SOLA GİT (Sadece sağ kol katlıysa)
                elif sag_kol_katli and not sol_kol_katli:
                    yeni_kontrol = 'LEFT'
                
                # 4. EĞİLME/ÇÖMELME (Basit Y koordinat kontrolü, isteğe bağlı)
                # Buraya iskeletin yüksekliğine göre çömelme mantığı tekrar eklenebilir.
                
                
                # --- KOMUT GÖNDERME ---
                if yeni_kontrol != aktif_kontrol:
                    print(f"KOMUT GÖNDERİLDİ: {yeni_kontrol}")
                    
                    # Eğer 'NONE' değilse tuş komutunu gönder
                    if yeni_kontrol != 'NONE':
                        pyautogui.press(yeni_kontrol.lower())
                    
                    aktif_kontrol = yeni_kontrol

                # Görüntüye açıları ve aktif komutu yazdır
                cv2.putText(image, f"SOL ACI: {int(sol_aci)} ({'KATLI' if sol_kol_katli else 'AÇIK'})", (20, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(image, f"SAG ACI: {int(sag_aci)} ({'KATLI' if sag_kol_katli else 'AÇIK'})", (20, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                cv2.putText(image, f"AKTIF KOMUT: {aktif_kontrol}", (20, 110), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
                
            except Exception as e:
                # Bazen MediaPipe noktaları bulamaz (özellikle kameradan uzaksanız)
                pass

            # İskelet Noktalarını Çizdirme
            mp_drawing.draw_landmarks(image, results.pose_landmarks, mp_pose.POSE_CONNECTIONS)
        
        # Görüntüyü Ekrana Çıkarma
        cv2.imshow('Aci Bazli Kol Kontrol', image)
        
        # Çıkış Komutu: 'ESC' tuşuna basılırsa döngüden çık
        if cv2.waitKey(10) & 0xFF == 27:
            break

# Kaynakları serbest bırakma ve pencereleri kapatma
cap.release()
cv2.destroyAllWindows()
print("Program sonlandı.")