# Eşikler burada — davranışı değiştirmek için kod değil, bu değerleri düzenle.

# --- Aday token filtresi (DexScreener) ---
CHAIN_ID = "solana"
MIN_LIQUIDITY_USD = 20_000        # havuzda en az bu kadar likidite olmalı
MIN_VOLUME_H24_USD = 50_000       # son 24 saat hacim
MIN_AGE_MINUTES = 15              # bu kadar yeni olmayan token'lar (ilk dakikalar rug riski yüksek)
MAX_AGE_HOURS = 24                # "yeni" sayılacak üst sınır
MAX_TOP_PAIR_CANDIDATES = 40      # her koşuda en fazla bu kadar aday derinlemesine incelenir (RPC/rate-limit koruması)

# --- Proje sağlamlık kontrolü (Solana RPC) ---
REQUIRE_MINT_AUTHORITY_NULL = True     # yeni token basılamıyor olmalı
REQUIRE_FREEZE_AUTHORITY_NULL = True   # dev cüzdanlar donduramıyor olmalı

# --- Yüklü alım (whale buy) tespiti ---
MIN_WHALE_BUY_USD = 5_000         # tek işlemde bu tutarın üstü "yüklü alım" sayılır
WHALE_LOOKBACK_TX = 30            # aday başına incelenecek son işlem sayısı

# --- Dedupe / mail ---
DEDUPE_HOURS = 12                 # aynı token için bu süre içinde ikinci mail atılmaz
SEEN_FILE = "seen.json"

# --- Solana public RPC (ücretsiz, key gerekmez) ---
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# --- DexScreener (ücretsiz, key gerekmez) ---
DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
DEXSCREENER_SEARCH_QUERIES = ["solana", "raydium", "pumpswap"]
