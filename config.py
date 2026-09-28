# Eşikler burada — davranışı değiştirmek için kod değil, bu değerleri düzenle.

# --- Aday token filtresi (DexScreener) ---
CHAIN_ID = "solana"
MIN_LIQUIDITY_USD = 50_000        # havuzda en az bu kadar likidite olmalı
MIN_VOLUME_H24_USD = 250_000      # son 24 saat hacim
MIN_AGE_MINUTES = 30              # bu kadar yeni olmayan token'lar (ilk dakikalar rug riski yüksek)
MAX_AGE_HOURS = 24                # "yeni" sayılacak üst sınır
MAX_TOP_PAIR_CANDIDATES = 40      # her koşuda en fazla bu kadar aday derinlemesine incelenir (RPC/rate-limit koruması)

# --- Proje sağlamlık kontrolü (Solana RPC) ---
REQUIRE_MINT_AUTHORITY_NULL = True     # yeni token basılamıyor olmalı
REQUIRE_FREEZE_AUTHORITY_NULL = True   # dev cüzdanlar donduramıyor olmalı

# --- Yüklü alım (whale buy) tespiti — GeckoTerminal ---
MIN_WHALE_BUY_USD = 5_000         # tek işlemde bu tutarın üstü "yüklü alım" sayılır
MIN_WHALE_WALLETS = 2             # en az bu kadar FARKLI cüzdan yüklü alım yapmış olmalı
MIN_TOTAL_WHALE_BUY_USD = 20_000  # yüklü alımların toplamı
REQUIRE_NET_POSITIVE = True       # yüklü alım toplamı yüklü satıştan büyük olmalı
EXCLUDE_ROUND_TRIP_WALLETS = True # aynı dönemde hem alıp hem satan cüzdan (arbitraj/MEV botu) sayılmaz
EXCLUDE_OPEN_AUTHORITY = True     # mint/freeze authority açık tokenlar hiç bildirilmez
GECKO_MIN_INTERVAL_SEC = 2.1     # ücretsiz limit ~30 istek/dk
FIRST_SEEN_LOOKBACK_HOURS = 1     # ilk kez görülen havuzda bu kadar geriye bak

# --- İzlenen cüzdanlar (fomo profilleri vb.) — ad: Solana adresi ---
WATCH_WALLETS = {
    # "CryptoKemal": "<solana cüzdan adresi>",
}
WALLET_LOOKBACK_TX = 25           # cüzdan başına koşu başı incelenecek son işlem
WALLET_FIRST_RUN_HOURS = 24       # yeni eklenen cüzdanda bu kadar geriye bak

# --- Durum ---
SEEN_FILE = "seen.json"           # havuz/cüzdan başına son bakılan zaman
SEEN_PRUNE_HOURS = 72             # bu kadar süredir bakılmayan havuz kaydı silinir

# --- Solana public RPC (ücretsiz, key gerekmez) ---
SOLANA_RPC_URL = "https://api.mainnet-beta.solana.com"

# --- DexScreener (ücretsiz, key gerekmez) ---
DEXSCREENER_SEARCH_URL = "https://api.dexscreener.com/latest/dex/search"
DEXSCREENER_SEARCH_QUERIES = ["solana", "raydium", "pumpswap"]
DEXSCREENER_TOKENS_URL = "https://api.dexscreener.com/latest/dex/tokens/"
