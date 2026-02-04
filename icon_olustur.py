"""
Temizlik Asistanı için süpürge temalı icon oluşturur.
"""
from PIL import Image, ImageDraw
import os

def supurge_icon_olustur(boyut=256):
    """Modern süpürge ikonu oluşturur"""
    
    # RGBA formatında şeffaf arka plan
    img = Image.new('RGBA', (boyut, boyut), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    # Ölçekleme faktörü
    s = boyut / 256
    
    # Arka plan - yuvarlatılmış kare (gradient efekti için)
    # Ana renk: Mavi tonları
    for i in range(int(20*s)):
        alpha = 255 - i * 2
        renk = (41, 128, 185, alpha)  # Mavi
        draw.rounded_rectangle(
            [10*s + i, 10*s + i, 246*s - i, 246*s - i],
            radius=40*s - i,
            fill=renk
        )
    
    # Ana arka plan
    draw.rounded_rectangle(
        [15*s, 15*s, 241*s, 241*s],
        radius=35*s,
        fill=(52, 152, 219, 255)  # Açık mavi
    )
    
    # Parlaklık efekti (üst kısım)
    draw.rounded_rectangle(
        [20*s, 20*s, 236*s, 100*s],
        radius=30*s,
        fill=(93, 173, 226, 180)  # Daha açık mavi, yarı saydam
    )
    
    # === SÜPÜRGE ===
    
    # Süpürge sapı (kahverengi)
    sap_renk = (139, 90, 43, 255)  # Kahverengi
    sap_highlight = (180, 130, 70, 255)  # Açık kahverengi
    
    # Sap - ana gövde (eğik)
    draw.polygon([
        (175*s, 45*s),   # Üst sağ
        (185*s, 50*s),   # Üst sağ köşe
        (95*s, 175*s),   # Alt sol
        (85*s, 170*s),   # Alt sol köşe
    ], fill=sap_renk)
    
    # Sap highlight
    draw.polygon([
        (177*s, 48*s),
        (182*s, 51*s),
        (92*s, 173*s),
        (87*s, 170*s),
    ], fill=sap_highlight)
    
    # Süpürge başlığı (fırça kısmı) - yeşil tonları
    fırca_renk = (46, 204, 113, 255)  # Yeşil
    fırca_koyu = (39, 174, 96, 255)   # Koyu yeşil
    
    # Fırça tabanı
    draw.ellipse([55*s, 160*s, 145*s, 190*s], fill=fırca_koyu)
    
    # Fırça kılları
    for i in range(9):
        x_offset = 65*s + i * 8*s
        # Her kıl için
        draw.polygon([
            (x_offset, 175*s),
            (x_offset + 6*s, 175*s),
            (x_offset + 3*s - i*2*s, 230*s),
            (x_offset - i*2*s, 228*s),
        ], fill=fırca_renk if i % 2 == 0 else fırca_koyu)
    
    # Fırça bağlantı halkası
    draw.ellipse([75*s, 162*s, 115*s, 182*s], fill=(241, 196, 15, 255))  # Sarı
    draw.ellipse([80*s, 166*s, 110*s, 178*s], fill=(243, 156, 18, 255))   # Turuncu
    
    # === PIRIŞ EFEKTI ===
    # Küçük yıldızlar/parıltılar
    parlak_renk = (255, 255, 255, 255)
    
    # Yıldız 1
    draw.ellipse([190*s, 80*s, 200*s, 90*s], fill=parlak_renk)
    # Yıldız 2
    draw.ellipse([200*s, 120*s, 208*s, 128*s], fill=parlak_renk)
    # Yıldız 3
    draw.ellipse([160*s, 100*s, 166*s, 106*s], fill=parlak_renk)
    
    return img

def icon_kaydet(img, dosya_adi):
    """Görüntüyü ICO formatında kaydeder"""
    # Farklı boyutlarda iconlar
    boyutlar = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    
    icon_imgs = []
    for boyut in boyutlar:
        resized = img.resize(boyut, Image.Resampling.LANCZOS)
        icon_imgs.append(resized)
    
    # ICO olarak kaydet
    img.save(dosya_adi, format='ICO', sizes=[(i.width, i.height) for i in icon_imgs])
    print(f"✅ Icon oluşturuldu: {dosya_adi}")
    
    # PNG olarak da kaydet (önizleme için)
    png_adi = dosya_adi.replace('.ico', '.png')
    img.save(png_adi, format='PNG')
    print(f"✅ PNG önizleme: {png_adi}")

if __name__ == "__main__":
    print("🎨 Süpürge temalı icon oluşturuluyor...")
    
    # 256x256 boyutunda icon oluştur
    icon = supurge_icon_olustur(256)
    
    # Kaydet
    script_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(script_dir, "asistan.ico")
    
    icon_kaydet(icon, icon_path)
    
    print("\n🧹 Temizlik Asistanı iconu hazır!")
