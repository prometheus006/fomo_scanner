# fomo_scanner

Solana üzerinde yeni çıkan, likidite/hacim/yaş filtresini geçen ve mint/freeze
authority'si kapatılmış ("rug basamayan") tokenları tarar; ayrıca bu adaylarda
son işlemlerde tek seferde `MIN_WHALE_BUY_USD` üstü alım olup olmadığına bakar.
Bulduklarını Gmail'e mail atar. GitHub Actions'ta saatlik çalışır (bkz.
`.github/workflows/scan.yml`), cron-job.org'dan `repository_dispatch` ile de
tetiklenebilir (quantfury_scanner/crypto_scanner ile aynı desen).

Veri kaynakları tamamen ücretsiz: DexScreener public API + Solana public RPC.
Ücretli bir API/anahtar kullanılmıyor.

## Eşikler (`config.py`)

| Değer | Anlamı |
|---|---|
| `MIN_LIQUIDITY_USD` | Havuzda en az bu kadar likidite |
| `MIN_VOLUME_H24_USD` | Son 24 saat hacim eşiği |
| `MIN_AGE_MINUTES` / `MAX_AGE_HOURS` | "Yeni" sayılacak yaş aralığı |
| `REQUIRE_MINT_AUTHORITY_NULL` / `REQUIRE_FREEZE_AUTHORITY_NULL` | Basım/dondurma yetkisi kapalı mı |
| `MIN_WHALE_BUY_USD` | Tek işlemde "yüklü alım" sayılacak tutar |
| `DEDUPE_HOURS` | Aynı token için tekrar mail atma aralığı |

## Kurulum (GitHub reposu oluşturulduktan sonra)

Repo ayarlarında **Settings → Secrets and variables → Actions** altına ekle:

- `SMTP_USER` — mail gönderen Gmail adresi
- `SMTP_PASS` — Gmail app password (normal şifre değil, Google
  hesap ayarlarından "App Passwords" ile üretilir)
- `SMTP_TO` — (opsiyonel) hedef adres, boşsa `SMTP_USER`'e gider

Durum dosyası `seen.json` repoya commit'lenmez, GitHub Actions önbelleğinde
(cache) tutulur; repodaki kopya yalnızca önbellek boşsa başlangıç değeridir.
Önbellek 7 gün kullanılmazsa GitHub siler — o zaman bir sonraki koşu repodaki
eski kopyayla başlar (birkaç tekrar bildirim olabilir).

## Sınırlamalar (bilinçli basitleştirmeler)

- Holder dağılımı / dev cüzdan geçmişi kontrolü YOK — sadece mint/freeze
  authority + likidite/hacim filtresi. Eklenmek istenirse Solscan/Helius gibi
  ek bir veri kaynağı gerekir (ücretsiz katmanları var ama ayrı kayıt ister).
- Yüklü alım tespiti pair adresinin son `WHALE_LOOKBACK_TX` işlemine bakar,
  tüm geçmişi taramaz — public RPC rate-limit'i yüzünden.
- Public Solana RPC (`api.mainnet-beta.solana.com`) ağır kullanımda
  yavaşlayabilir/limitleyebilir; aday sayısı `MAX_TOP_PAIR_CANDIDATES` ile
  sınırlı tutuluyor.
