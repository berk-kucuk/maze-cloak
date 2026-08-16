"""English and Turkish strings.

`t()` falls back to English and then to the key itself, so a missing
translation shows an untranslated label rather than an empty widget — the tests
check that the two tables have the same keys, which is what actually keeps them
in step.
"""

STRINGS: dict[str, dict[str, str]] = {
    "en": {
        # ── shell ──────────────────────────────────────────────────────────
        "app_name": "MAZE CLOAK",
        "tab_overview": "Overview",
        "tab_interfaces": "Interfaces",
        "tab_schedule": "Schedule",
        "tab_settings": "Settings",
        "tip_minimize": "Minimize",
        "tip_maximize": "Maximize / Restore",
        "tip_close": "Minimize to tray",

        # ── overview ───────────────────────────────────────────────────────
        "state_on": "Cloaked",
        "state_off": "Not cloaked",
        "state_paused_vpn": "Paused — VPN active",
        "state_no_schedule": "Cloaked — manual rotation only",
        "state_daemon_off": "Daemon not running",
        "state_stale": "Daemon stopped unexpectedly",
        "btn_enable": "ENABLE CLOAK",
        "btn_disable": "DISABLE CLOAK",
        "btn_rotate_now": "Rotate now",

        "hero_showing": "SHOWING ON THE NETWORK",
        "hero_appears_as": "appears as",
        "hero_no_vendor": "no vendor behind it",
        "hero_hardware": "hardware",
        "hero_exposed": "this is your permanent address",
        "sec_cloaked_interfaces": "CLOAKED INTERFACES",

        "card_rotation": "Rotation",
        "card_identity": "Identity",
        "card_integration": "Maze integration",

        "lbl_next": "Next",
        "lbl_last": "Last",
        "lbl_count": "Rotations",
        "lbl_strategy": "Strategy",
        "lbl_interval": "Every",
        "lbl_interfaces": "Interfaces",
        "lbl_never": "never",
        "lbl_due": "due now",
        "lbl_unknown": "unknown",
        "lbl_none": "none",

        "nm_active": "Reported to Maze tools",
        "nm_inactive": "Not reported",
        "nm_elsewhere": "Enabled by another tool",
        "nm_hint": "Maze Control Center reads this to show your MAC randomisation status.",

        "daemon_running": "Running",
        "daemon_stopped": "Stopped",
        "daemon_missing": "Not installed",
        "btn_daemon_start": "Start daemon",
        "btn_daemon_stop": "Stop daemon",

        # ── interfaces ─────────────────────────────────────────────────────
        "col_interface": "INTERFACE",
        "col_current": "CURRENT MAC",
        "col_hardware": "HARDWARE MAC",
        "col_vendor": "VENDOR",
        "col_type": "TYPE",
        "col_state": "STATE",
        "col_cloak": "CLOAK",
        "type_wireless": "Wi-Fi",
        "type_wired": "Ethernet",
        "state_up": "up",
        "state_down": "down",
        "iface_hint": "Untick an interface to leave its address alone. "
                      "With nothing ticked, every physical interface is rotated.",
        "iface_empty": "No physical network interfaces found.",
        "btn_rotate_iface": "Rotate",
        "btn_restore_iface": "Restore",

        # ── schedule ───────────────────────────────────────────────────────
        "sched_group": "ROTATION",
        "sched_enable": "Rotate the address on a timer",
        "sched_interval": "Rotation interval:",
        "sched_minutes": "minutes",
        "sched_on_start": "Rotate immediately when the cloak is enabled",
        "sched_pause_vpn": "Pause while a VPN tunnel is up",
        "sched_pause_vpn_hint": "Changing the address bounces the link the tunnel "
                               "runs over, which drops the VPN.",
        "sched_restore": "Restore the hardware address when the cloak is turned off",

        "strategy_group": "ADDRESS STYLE",
        "strategy_full_random": "Fully random",
        "strategy_full_random_desc": "Every byte random. Maximum unlinkability, but "
                                     "stands out on a network of recognisable vendors.",
        "strategy_keep_vendor": "Keep my vendor prefix",
        "strategy_keep_vendor_desc": "Keeps the first three bytes of the hardware "
                                     "address, randomises the rest. Blends in; leaks "
                                     "your adapter's make.",
        "strategy_random_vendor": "Random vendor prefix",
        "strategy_random_vendor_desc": "Borrows the shape of a common consumer OUI. "
                                       "Blends in without revealing your hardware.",

        # ── settings ───────────────────────────────────────────────────────
        "set_nm_group": "NETWORKMANAGER",
        "set_nm_enable": "Let NetworkManager randomise as well",
        "set_nm_scan": "Randomise the address used while scanning for networks",
        "set_nm_scan_hint": "Applies before you connect to anything — this is the "
                           "address every access point in range sees.",
        "set_nm_cloned": "Address once connected:",
        "cloned_random": "New address every connection",
        "cloned_stable": "Stable per network",
        "cloned_stable_hint": "Stable keeps captive portals and MAC-based Wi-Fi "
                             "allowlists working.",

        "set_daemon_group": "DAEMON",
        "set_daemon_hint": "The daemon performs the rotation. It runs as root under "
                          "systemd; this window only writes settings.",
        "set_autostart": "Start Maze Cloak on login",
        "set_autostart_hint": "On by default. Rotation itself is the daemon's job and "
                             "continues whether or not this window is open.",

        "set_ui_group": "INTERFACE",
        "set_theme": "Theme:",
        "set_language": "Language:",
        "set_start_hidden": "Start hidden in the system tray",
        "set_notify": "Notify when the address changes",

        "theme_dark": "Dark",
        "theme_light": "Light",

        # ── banners & messages ─────────────────────────────────────────────
        "warn_readonly": "Settings are read-only: this account cannot write "
                        "{path}. Add yourself to the '{group}' group and log back in.",
        "warn_no_daemon": "The Maze Cloak daemon is not installed. "
                         "Run scripts/setup-daemon.sh to install it.",
        "warn_daemon_stopped": "The daemon is installed but not running — nothing "
                              "is rotating.",
        "warn_no_hw_addr": "The hardware address of {iface} could not be read, so it "
                          "cannot be restored later.",
        "err_save": "Could not save settings: {err}",
        "err_service": "Could not control the daemon: {err}",
        "msg_cancelled": "Cancelled.",
        "msg_rotated": "{count} interface(s) rotated.",
        "msg_rotate_failed": "Rotation failed: {err}",

        # ── tray ───────────────────────────────────────────────────────────
        "tray_show": "Show",
        "tray_enable": "Enable cloak",
        "tray_disable": "Disable cloak",
        "tray_rotate": "Rotate now",
        "tray_quit": "Quit",
        "notify_title": "Maze Cloak",
        "notify_rotated": "New address on {iface}: {mac}",
        "notify_enabled": "Cloak enabled — your MAC address is now randomised.",
        "notify_disabled": "Cloak disabled — hardware address restored.",
    },

    "tr": {
        # ── shell ──────────────────────────────────────────────────────────
        "app_name": "MAZE CLOAK",
        "tab_overview": "Genel Bakış",
        "tab_interfaces": "Arayüzler",
        "tab_schedule": "Zamanlama",
        "tab_settings": "Ayarlar",
        "tip_minimize": "Küçült",
        "tip_maximize": "Büyüt / Geri al",
        "tip_close": "Sistem tepsisine indir",

        # ── overview ───────────────────────────────────────────────────────
        "state_on": "Gizlenmiş",
        "state_off": "Gizlenmemiş",
        "state_paused_vpn": "Duraklatıldı — VPN etkin",
        "state_no_schedule": "Gizlenmiş — yalnızca elle değiştirme",
        "state_daemon_off": "Servis çalışmıyor",
        "state_stale": "Servis beklenmedik şekilde durdu",
        "btn_enable": "GİZLEMEYİ AÇ",
        "btn_disable": "GİZLEMEYİ KAPAT",
        "btn_rotate_now": "Şimdi değiştir",

        "hero_showing": "AĞA GÖSTERİLEN ADRES",
        "hero_appears_as": "şöyle görünüyor:",
        "hero_no_vendor": "arkasında üretici yok",
        "hero_hardware": "donanım",
        "hero_exposed": "bu sizin kalıcı adresiniz",
        "sec_cloaked_interfaces": "GİZLENEN ARAYÜZLER",

        "card_rotation": "Değişim",
        "card_identity": "Kimlik",
        "card_integration": "Maze entegrasyonu",

        "lbl_next": "Sonraki",
        "lbl_last": "Son",
        "lbl_count": "Değişim sayısı",
        "lbl_strategy": "Yöntem",
        "lbl_interval": "Sıklık",
        "lbl_interfaces": "Arayüzler",
        "lbl_never": "hiç",
        "lbl_due": "şimdi",
        "lbl_unknown": "bilinmiyor",
        "lbl_none": "yok",

        "nm_active": "Maze araçlarına bildiriliyor",
        "nm_inactive": "Bildirilmiyor",
        "nm_elsewhere": "Başka bir araç tarafından açılmış",
        "nm_hint": "Maze Control Center, MAC randomizasyon durumunuzu buradan okur.",

        "daemon_running": "Çalışıyor",
        "daemon_stopped": "Durduruldu",
        "daemon_missing": "Kurulu değil",
        "btn_daemon_start": "Servisi başlat",
        "btn_daemon_stop": "Servisi durdur",

        # ── interfaces ─────────────────────────────────────────────────────
        "col_interface": "ARAYÜZ",
        "col_current": "GÜNCEL MAC",
        "col_hardware": "DONANIM MAC",
        "col_vendor": "ÜRETİCİ",
        "col_type": "TÜR",
        "col_state": "DURUM",
        "col_cloak": "GİZLE",
        "type_wireless": "Wi-Fi",
        "type_wired": "Ethernet",
        "state_up": "açık",
        "state_down": "kapalı",
        "iface_hint": "Adresine dokunulmasını istemediğiniz arayüzün işaretini kaldırın. "
                      "Hiçbiri işaretli değilse tüm fiziksel arayüzler değiştirilir.",
        "iface_empty": "Fiziksel ağ arayüzü bulunamadı.",
        "btn_rotate_iface": "Değiştir",
        "btn_restore_iface": "Geri yükle",

        # ── schedule ───────────────────────────────────────────────────────
        "sched_group": "DEĞİŞİM",
        "sched_enable": "Adresi zamanlayıcıyla değiştir",
        "sched_interval": "Değişim aralığı:",
        "sched_minutes": "dakika",
        "sched_on_start": "Gizleme açıldığında hemen değiştir",
        "sched_pause_vpn": "VPN tüneli açıkken duraklat",
        "sched_pause_vpn_hint": "Adresi değiştirmek tünelin üzerinde çalıştığı bağlantıyı "
                               "sıfırlar ve VPN düşer.",
        "sched_restore": "Gizleme kapatıldığında donanım adresini geri yükle",

        "strategy_group": "ADRES BİÇİMİ",
        "strategy_full_random": "Tamamen rastgele",
        "strategy_full_random_desc": "Her bayt rastgele. En yüksek takip edilemezlik, "
                                     "ama tanıdık üreticilerin olduğu bir ağda göze çarpar.",
        "strategy_keep_vendor": "Üretici önekimi koru",
        "strategy_keep_vendor_desc": "Donanım adresinin ilk üç baytını korur, gerisini "
                                     "rastgeleleştirir. Göze çarpmaz; adaptörünüzün "
                                     "markasını açık eder.",
        "strategy_random_vendor": "Rastgele üretici öneki",
        "strategy_random_vendor_desc": "Yaygın bir tüketici OUI'sinin biçimini ödünç alır. "
                                       "Donanımınızı ele vermeden göze çarpmaz.",

        # ── settings ───────────────────────────────────────────────────────
        "set_nm_group": "NETWORKMANAGER",
        "set_nm_enable": "NetworkManager da rastgeleleştirsin",
        "set_nm_scan": "Ağ taraması sırasında kullanılan adresi rastgeleleştir",
        "set_nm_scan_hint": "Herhangi bir ağa bağlanmadan önce geçerlidir — menzildeki "
                           "her erişim noktasının gördüğü adres budur.",
        "set_nm_cloned": "Bağlandıktan sonraki adres:",
        "cloned_random": "Her bağlantıda yeni adres",
        "cloned_stable": "Ağ başına sabit",
        "cloned_stable_hint": "Sabit seçeneği, giriş portallarının ve MAC tabanlı Wi-Fi "
                             "izin listelerinin çalışmasını sürdürür.",

        "set_daemon_group": "SERVİS",
        "set_daemon_hint": "Değişimi servis gerçekleştirir. systemd altında root olarak "
                          "çalışır; bu pencere yalnızca ayarları yazar.",
        "set_autostart": "Maze Cloak'u oturum açılışında başlat",
        "set_autostart_hint": "Varsayılan olarak açık. Adres değişimi servisin işidir ve "
                             "bu pencere kapalıyken de sürer.",

        "set_ui_group": "ARAYÜZ",
        "set_theme": "Tema:",
        "set_language": "Dil:",
        "set_start_hidden": "Sistem tepsisinde gizli başlat",
        "set_notify": "Adres değiştiğinde bildir",

        "theme_dark": "Koyu",
        "theme_light": "Açık",

        # ── banners & messages ─────────────────────────────────────────────
        "warn_readonly": "Ayarlar salt okunur: bu hesap {path} dosyasına yazamıyor. "
                        "Kendinizi '{group}' grubuna ekleyip yeniden oturum açın.",
        "warn_no_daemon": "Maze Cloak servisi kurulu değil. "
                         "Kurmak için scripts/setup-daemon.sh betiğini çalıştırın.",
        "warn_daemon_stopped": "Servis kurulu ama çalışmıyor — hiçbir şey değişmiyor.",
        "warn_no_hw_addr": "{iface} arayüzünün donanım adresi okunamadı, bu yüzden "
                          "sonradan geri yüklenemez.",
        "err_save": "Ayarlar kaydedilemedi: {err}",
        "err_service": "Servis denetlenemedi: {err}",
        "msg_cancelled": "İptal edildi.",
        "msg_rotated": "{count} arayüzün adresi değiştirildi.",
        "msg_rotate_failed": "Değişim başarısız: {err}",

        # ── tray ───────────────────────────────────────────────────────────
        "tray_show": "Göster",
        "tray_enable": "Gizlemeyi aç",
        "tray_disable": "Gizlemeyi kapat",
        "tray_rotate": "Şimdi değiştir",
        "tray_quit": "Çıkış",
        "notify_title": "Maze Cloak",
        "notify_rotated": "{iface} için yeni adres: {mac}",
        "notify_enabled": "Gizleme açık — MAC adresiniz artık rastgele.",
        "notify_disabled": "Gizleme kapalı — donanım adresi geri yüklendi.",
    },
}


def t(key: str, lang: str = "en") -> str:
    return STRINGS.get(lang, STRINGS["en"]).get(key, STRINGS["en"].get(key, key))
