"""EX SPORTS SFC 27 ONLINE networking (shared code path with SHINE ONLINE) - real internet play without any paid server.

How a session is reached
  * the host opens one UDP socket (default port 47115) and asks public STUN servers what address the internet sees
  * it also asks the home router (UPnP IGD) to forward that UDP port - if the router agrees, anyone can join directly
  * the host's public address + port + a random nonce are packed into a JOIN CODE:  SFC27-XXXX-XXXX (port 47127 kept)
    or SFC27-XXXX-XXXX-XXXX (any other port)
  * joiners decode the code and keep sending signed HELLO packets to that address (UDP hole punching); the host answers
  * if the host's router is strict, the joiner shows a REPLY CODE: the host types it under LET A FRIEND IN and punches back
  * if nothing gets through the game says exactly which UDP port the host should forward
  * on the same Wi-Fi, LAN discovery lists sessions automatically
Every packet carries an HMAC-SHA256 tag keyed by the join code (+ the optional password); anything else is dropped."""
import socket, threading, json, hmac, hashlib, os, time, random, struct, queue, re, urllib.request, urllib.parse

PORT = 47127
LAN_PORT = 47128
STUN_SERVERS = [("stun.l.google.com", 19302), ("stun1.l.google.com", 19302), ("stun.cloudflare.com", 3478), ("stun.nextcloud.com", 3478)]
B32 = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
MAGIC = 0x2112A442
VER = 1
TAG = 16


def _b32(n, chars):
    return "".join(B32[(n >> (5 * (chars - 1 - i))) & 31] for i in range(chars))


def make_code(ip, port, nonce):
    """ip:port + nonce -> SFC27-XXXX-XXXX (port 47115) or SFC27-XXXX-XXXX-XXXX"""
    ipn = struct.unpack("!I", socket.inet_aton(ip))[0]
    if port == PORT:
        s = _b32((ipn << 8) | (nonce & 0xFF), 8)
    else:
        s = _b32((ipn << 28) | ((port & 0xFFFF) << 12) | (nonce & 0xFFF), 12)
    return "SFC27-" + "-".join(s[i:i + 4] for i in range(0, len(s), 4))


def norm_code(code):
    s = str(code or "").upper().replace("O", "0").replace("I", "1").replace("L", "1")
    s = re.sub(r"[^0-9A-Z]", "", s)
    if s.startswith("SH1NE"): s = s[5:]
    elif s.startswith("SFC27"): s = s[5:]
    return s


def parse_code(code):
    """join code -> (ip, port, canonical code) or None"""
    s = norm_code(code)
    if len(s) not in (8, 12) or any(ch not in B32 for ch in s): return None
    n = 0
    for ch in s: n = (n << 5) | B32.index(ch)
    if len(s) == 8: ipn, port = n >> 8, PORT
    else: ipn, port = n >> 28, (n >> 12) & 0xFFFF
    if port == 0: return None
    ip = socket.inet_ntoa(struct.pack("!I", ipn))
    return ip, port, "SFC27-" + "-".join(s[i:i + 4] for i in range(0, len(s), 4))


def session_key(code, password=""):
    return hashlib.sha256(("SFC27|%s|%s" % (norm_code(code), password or "")).encode()).digest()


LAN_KEY = hashlib.sha256(b"SFC27-LAN").digest()


def seal(key, msg):
    body = json.dumps(msg, separators=(",", ":")).encode()
    return b"SH1" + body + hmac.new(key, b"SH1" + body, hashlib.sha256).digest()[:TAG]


def open_(key, data):
    if len(data) < 3 + TAG + 2 or data[:3] != b"SH1": return None
    body, tag = data[3:-TAG], data[-TAG:]
    if not hmac.compare_digest(tag, hmac.new(key, b"SH1" + body, hashlib.sha256).digest()[:TAG]): return None
    try:
        m = json.loads(body.decode())
        return m if isinstance(m, dict) else None
    except Exception:
        return None


def local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(("10.255.255.255", 1)); ip = s.getsockname()[0]; s.close(); return ip
    except Exception:
        return "127.0.0.1"


def is_private(ip):
    try:
        a, b = [int(x) for x in ip.split(".")[:2]]
    except Exception:
        return True
    return a in (10, 127) or (a == 192 and b == 168) or (a == 172 and 16 <= b <= 31) or (a == 100 and 64 <= b <= 127) or a == 169


# ------------------------------------------------------------------ UPnP IGD port mapping (best effort)
class UPnP:
    def __init__(self): self.ctrl = None; self.svc = None; self.ext_ip = None; self.mapped = None; self.err = ""

    def discover(self, timeout=2.0):
        msg = ("M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nMAN: \"ssdp:discover\"\r\nMX: 2\r\n"
               "ST: urn:schemas-upnp-org:device:InternetGatewayDevice:1\r\n\r\n").encode()
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.settimeout(timeout)
        locs = []
        try:
            s.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            for _ in range(2): s.sendto(msg, ("239.255.255.250", 1900))
            t0 = time.time()
            while time.time() - t0 < timeout:
                try: data, _a = s.recvfrom(4096)
                except socket.timeout: break
                m = re.search(rb"(?im)^location:\s*(\S+)", data)
                if m and m.group(1).decode() not in locs: locs.append(m.group(1).decode())
        except Exception as e:
            self.err = str(e)
        finally:
            s.close()
        for loc in locs:
            try:
                xml = urllib.request.urlopen(loc, timeout=2.5).read().decode("utf-8", "ignore")
                for st in ("urn:schemas-upnp-org:service:WANIPConnection:1", "urn:schemas-upnp-org:service:WANIPConnection:2",
                           "urn:schemas-upnp-org:service:WANPPPConnection:1"):
                    i = xml.find(st)
                    if i < 0: continue
                    m = re.search(r"<controlURL>\s*([^<]+)\s*</controlURL>", xml[i:])
                    if m:
                        self.ctrl = urllib.parse.urljoin(loc, m.group(1).strip()); self.svc = st; return True
            except Exception as e:
                self.err = str(e)
        if not self.err: self.err = "no UPnP router answered"
        return False

    def _soap(self, action, args):
        body = "".join("<%s>%s</%s>" % (k, v, k) for k, v in args)
        env = ('<?xml version="1.0"?><s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
               's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/"><s:Body><u:%s xmlns:u="%s">%s</u:%s></s:Body></s:Envelope>'
               % (action, self.svc, body, action)).encode()
        rq = urllib.request.Request(self.ctrl, env, {"Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": '"%s#%s"' % (self.svc, action)})
        return urllib.request.urlopen(rq, timeout=3).read().decode("utf-8", "ignore")

    def map(self, port, lip):
        if not self.ctrl and not self.discover(): return False
        try:
            r = self._soap("GetExternalIPAddress", [])
            m = re.search(r"<NewExternalIPAddress>([^<]*)<", r)
            if m and m.group(1): self.ext_ip = m.group(1)
            self._soap("AddPortMapping", [("NewRemoteHost", ""), ("NewExternalPort", port), ("NewProtocol", "UDP"), ("NewInternalPort", port),
                                          ("NewInternalClient", lip), ("NewEnabled", 1), ("NewPortMappingDescription", "EX SPORTS SFC 27"),
                                          ("NewLeaseDuration", 7200)])
            self.mapped = port; return True
        except Exception as e:
            self.err = "router refused port mapping (%s)" % (str(e)[:60]); return False

    def unmap(self):
        if self.mapped and self.ctrl:
            try: self._soap("DeletePortMapping", [("NewRemoteHost", ""), ("NewExternalPort", self.mapped), ("NewProtocol", "UDP")])
            except Exception: pass
        self.mapped = None


# ------------------------------------------------------------------ session
class Session:
    """one UDP socket. role 'host' or 'join'. Call poll() every frame from the game thread; read .events for UI."""
    def __init__(self, role, name="PLAYER", cfg=None, password="", port=None, upnp=True, stun=True, sim_firewall=None):
        self.role = role; self.name = name; self.cfg = cfg or {}; self.password = password or ""
        self.events = []; self.peers = {}; self.my_id = 0 if role == "host" else None; self.state = "starting"
        self.status = ""; self.code = None; self.key = None; self.key0 = None; self.public = None; self.via = ""
        self.inbox = queue.Queue(); self.alive = True; self.handlers = {}; self.host_addr = None
        self.ping_ms = None; self._ping_t = 0.0; self._roster_t = 0.0; self._hello_t = 0.0; self._lan_t = 0.0
        self.joined_at = None; self.join_started = None; self.reachable = False; self.remote_states = {}; self.chat = []
        self.kicked = False; self.nonce = random.getrandbits(12); self.upnp = UPnP() if upnp else None
        self.lip = local_ip(); self._stun_tx = {}; self._next_id = 1; self.punch_to = []
        # v1.0.5.1: everything is outbound-first. A stateful firewall (Windows Defender Firewall with no rule, or the user
        # dismissed its prompt) only lets in packets from addresses this socket has already sent to, so: the guest calls the
        # host, the host calls the guest (reply code / LAN), and keep-alives hold both doors open. sim_firewall drops
        # everything else, to test exactly that.
        self.sim_fw = bool(sim_firewall if sim_firewall is not None else os.environ.get("FS_NET_SIMFW"))
        self._out = set(); self._bcast_t = 0.0; self.dropped = 0; self._ka_t = 0.0
        want = PORT if port is None else port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        for p in ([want, 0] if role == "host" else [0]):
            try: self.sock.bind(("0.0.0.0", p)); break
            except OSError: continue
        self.port = self.sock.getsockname()[1]
        self.sock.settimeout(0.25)
        threading.Thread(target=self._rx, daemon=True).start()
        self.lan = None
        if role == "host":
            self.override = os.environ.get("FS_NET_ADDR")
            threading.Thread(target=self._discover, args=(stun,), daemon=True).start()

    # ---- background I/O
    def _rx(self):
        while self.alive:
            try: data, addr = self.sock.recvfrom(65535)
            except socket.timeout: continue
            except OSError:
                if not self.alive: break
                time.sleep(0.05); continue
            lan_resp = time.time() - self._bcast_t < 3.0 and is_private(addr[0]) and not addr[0].startswith("127.")
            if self.sim_fw and addr not in self._out and not lan_resp:
                self.dropped += 1; continue           # unsolicited: a stateful firewall would drop it
            self.inbox.put((data, addr))

    def _tx(self, data, addr):
        """every datagram goes out through here, so we know which doors are open"""
        self._out.add((addr[0], int(addr[1])))
        if addr[0].endswith(".255"): self._bcast_t = time.time()
        self.sock.sendto(data, addr)

    def _stun(self, timeout=2.5):
        """ask every STUN server at once (same socket the game uses), first answer wins"""
        ev = threading.Event(); txs = []
        for host, port in STUN_SERVERS:
            try: ip = socket.gethostbyname(host)
            except Exception: continue
            tid = os.urandom(12); self._stun_tx[tid] = [ev, None]; txs.append((tid, (ip, port)))
        if not txs: return None
        t0 = time.time()
        while time.time() - t0 < timeout:
            for tid, addr in txs:
                try: self._tx(struct.pack("!HHI", 0x0001, 0, MAGIC) + tid, addr)
                except OSError: pass
            if ev.wait(0.8): break
        res = None
        for tid, _a in txs:
            r = self._stun_tx.pop(tid, [None, None])[1]
            res = res or r
        return res

    def _stun_parse(self, data):
        if len(data) < 20: return
        mt, ln, mc = struct.unpack("!HHI", data[:8]); tid = data[8:20]
        if mc != MAGIC or mt != 0x0101 or tid not in self._stun_tx: return
        i = 20
        while i + 4 <= len(data):
            at, al = struct.unpack("!HH", data[i:i + 4]); v = data[i + 4:i + 4 + al]
            if at in (0x0020, 0x0001) and len(v) >= 8 and v[1] == 1:
                port, ipn = struct.unpack("!HI", v[2:8])
                if at == 0x0020: port ^= MAGIC >> 16; ipn ^= MAGIC
                self._stun_tx[tid][1] = (socket.inet_ntoa(struct.pack("!I", ipn)), port); self._stun_tx[tid][0].set(); return
            i += 4 + al + ((4 - al % 4) % 4)

    def _discover(self, stun):
        ip, port, via = None, self.port, ""
        if self.override:
            ip, via = self.override, "TEST ADDRESS"
        else:
            res = {}
            def _up():
                res["mapped"] = self.upnp.map(self.port, self.lip) if self.upnp is not None else False
            th = threading.Thread(target=_up, daemon=True); th.start()          # router (UPnP) and STUN in parallel
            self.status = "FINDING YOUR INTERNET ADDRESS..."
            st = self._stun() if stun else None
            th.join(6.0); mapped = bool(res.get("mapped"))
            if mapped and (self.upnp.ext_ip and not is_private(self.upnp.ext_ip)):
                ip, port, via = self.upnp.ext_ip, self.port, "ROUTER PORT OPENED (UPnP)"
            elif st:
                ip, port = st; via = "PUBLIC ADDRESS VIA STUN" + (" + UPnP" if mapped else "")
                if mapped: port = self.port
            else:
                ip, via = self.lip, "LAN ONLY (NO INTERNET ADDRESS FOUND)"
        self.public = (ip, port); self.via = via
        self.code = make_code(ip, port, self.nonce)
        self.key = session_key(self.code, self.password); self.key0 = session_key(self.code, "")
        self.state = "hosting"; self.status = "SESSION OPEN"
        self.events.append(("code", self.code))
        try:
            self.lan = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); self.lan.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        except Exception:
            self.lan = None

    # ---- helpers
    def send(self, addr, msg, key=None):
        try: self._tx(seal(key or self.key, msg), addr)
        except OSError: pass

    def on(self, t, fn): self.handlers[t] = fn

    def forward_hint(self):
        return "ASK THE HOST TO FORWARD UDP PORT %d TO THEIR PC" % (self.host_addr[1] if self.host_addr else self.port)

    # ---- join side
    def join(self, code, addr=None):
        """addr: a LAN address found by LAN discovery (same code/key, but no trip through the router)"""
        p = parse_code(code)
        if not p: self.state = "error"; self.status = "THAT CODE LOOKS WRONG (SFC27-XXXX-XXXX)"; return False
        ip, port, self.code = p
        self.host_addr = tuple(addr) if addr else (ip, port); self.key = session_key(self.code, self.password); self.key0 = session_key(self.code, "")
        self.state = "joining"; self.status = "CALLING HOST..."; self.join_started = time.time()
        if not os.environ.get("FS_NET_ADDR"):
            threading.Thread(target=self._joiner_public, daemon=True).start()
        else:
            self.public = (os.environ["FS_NET_ADDR"], self.port)
        return True

    def _joiner_public(self):
        st = self._stun()
        self.public = st or (self.lip, self.port)

    def reply_code(self):
        """the joiner's own endpoint, for the host's LET A FRIEND IN box (strict routers)"""
        if not self.public: return None
        return make_code(self.public[0], self.public[1] if self.public[1] != PORT else PORT, random.getrandbits(8))

    def let_in(self, code):
        p = parse_code(code)
        if not p: return False
        ep = (p[0], p[1])
        for pt in self.punch_to:
            if pt[0] == ep: pt[1] = time.time() + 90.0; return True
        self.punch_to.append([ep, time.time() + 90.0, 0.0]); return True

    # ---- the frame pump
    def poll(self, now=None, my_state=None):
        now = now or time.time()
        while True:
            try: data, addr = self.inbox.get_nowait()
            except queue.Empty: break
            if len(data) >= 20 and data[4:8] == struct.pack("!I", MAGIC):
                self._stun_parse(data); continue
            if self.key is None: continue
            if self.role == "host" and self.code:
                lq = open_(LAN_KEY, data)
                if lq is not None:                       # a LAN game asked "anyone hosting?" by broadcast: answer it directly
                    if lq.get("t") == "lanq": self._lan_reply(addr)
                    continue
            m = open_(self.key, data); weak = False
            if m is None:
                m = open_(self.key0, data); weak = True
                if m is None or m.get("t") not in ("probe", "probe_ok"): continue
            try: self._handle(m, addr, now, weak)
            except Exception as e:
                self.events.append(("error", "bad packet: %s" % e))
        if self.role == "host": self._host_tick(now, my_state)
        else: self._join_tick(now, my_state)

    def _handle(self, m, addr, now, weak):
        t = m.get("t")
        if self.role == "host":
            if t == "probe":
                self.send(addr, {"t": "probe_ok", "pw": bool(self.password)}, self.key0); return
            if t == "hello":
                pid = None
                for k, p in self.peers.items():
                    if p["addr"] == addr: pid = k
                if pid is None:
                    if len(self.peers) >= 7: self.send(addr, {"t": "full"}); return
                    pid = self._next_id; self._next_id += 1
                    self.peers[pid] = {"addr": addr, "name": str(m.get("name", "FRIEND"))[:12], "cfg": m.get("cfg") or {}, "last": now, "ping": None, "state": None}
                    self.punch_to = [pt for pt in self.punch_to if pt[0] != addr]
                    self.events.append(("join", pid)); self._say("%s JOINED" % self.peers[pid]["name"], now)
                    self._roster_t = 0.0
                self.peers[pid]["last"] = now
                self.send(addr, {"t": "welcome", "id": pid, "host": self.name, "hcfg": self.cfg}); return
            pid = next((k for k, p in self.peers.items() if p["addr"] == addr), None)
            if pid is None: return
            p = self.peers[pid]; p["last"] = now
            if t == "st": p["state"] = m.get("s")
            elif t == "ping": self.send(addr, {"t": "pong", "c": m.get("c")})
            elif t == "pong":
                try: p["ping"] = int((now - float(m.get("c"))) * 1000)
                except Exception: pass
            elif t == "chat":
                self._say("%s: %s" % (p["name"], str(m.get("x", ""))[:80]), now, relay=True)
            elif t == "bye":
                self.events.append(("leave", pid)); self._say("%s LEFT" % p["name"], now); del self.peers[pid]; self._roster_t = 0.0
            elif t == "cfg":
                p["cfg"] = m.get("cfg") or p["cfg"]; p["name"] = str(m.get("name", p["name"]))[:12]; self._roster_t = 0.0
            elif t in self.handlers: self.handlers[t](pid, m)
        else:
            if addr != self.host_addr and t not in ("probe_ok",):
                if self.host_addr and addr[1] == self.host_addr[1]: pass
                else: return
            self.last_host = now
            if t == "probe_ok":
                self.reachable = True; self.need_pw = m.get("pw")
            elif t == "punch":                         # the host is calling us (reply code): answer at once
                if self.state == "joining":
                    self.send(self.host_addr, {"t": "hello", "name": self.name, "cfg": self.cfg, "v": VER})
            elif t == "welcome":
                if self.my_id is None:
                    self.events.append(("joined", m.get("id"))); self.joined_at = now
                self.my_id = m.get("id"); self.state = "joined"; self.status = "CONNECTED"; self.host_name = m.get("host"); self.host_cfg = m.get("hcfg")
            elif t == "roster":
                self.roster = m.get("p", [])
                for e in self.roster:
                    if e.get("id") == self.my_id: self.ping_ms = e.get("ping")
            elif t == "sts":
                self.remote_states = {int(k): v for k, v in (m.get("s") or {}).items() if int(k) != self.my_id}
            elif t == "ping": self.send(addr, {"t": "pong", "c": m.get("c")})
            elif t == "pong":
                try: self.ping_ms = int((now - float(m.get("c"))) * 1000)
                except Exception: pass
            elif t == "chat": self.chat.append(str(m.get("x", ""))[:100]); self.events.append(("chat", self.chat[-1]))
            elif t == "kick":
                self.kicked = True; self.state = "ended"; self.status = "THE HOST REMOVED YOU FROM THE SESSION"; self.events.append(("kicked", None))
            elif t == "end":
                self.state = "ended"; self.status = "THE HOST CLOSED THE SESSION"; self.events.append(("ended", None))
            elif t == "full":
                self.state = "error"; self.status = "SESSION IS FULL (8 PLAYERS)"
            elif t in self.handlers: self.handlers[t](0, m)

    def _say(self, text, now, relay=False):
        self.chat.append(text); self.events.append(("chat", text))
        for p in self.peers.values(): self.send(p["addr"], {"t": "chat", "x": text})

    def say(self, text):
        text = str(text)[:80]
        if not text: return
        if self.role == "host": self._say("%s: %s" % (self.name, text), time.time())
        elif self.state == "joined": self.send(self.host_addr, {"t": "chat", "x": text})

    def kick(self, pid):
        p = self.peers.pop(pid, None)
        if p:
            for _ in range(3): self.send(p["addr"], {"t": "kick"})
            self._say("%s WAS REMOVED" % p["name"], time.time()); self.events.append(("leave", pid)); self._roster_t = 0.0

    def broadcast(self, msg):
        for p in self.peers.values(): self.send(p["addr"], msg)

    def to_host(self, msg):
        if self.host_addr: self.send(self.host_addr, msg)

    def _host_tick(self, now, my_state):
        if self.key is None: return
        for pid in [k for k, p in self.peers.items() if now - p["last"] > 12.0]:
            nm = self.peers[pid]["name"]; del self.peers[pid]; self.events.append(("leave", pid)); self._say("%s LOST CONNECTION" % nm, now); self._roster_t = 0.0
        for pt in list(self.punch_to):                 # calling a guest from their reply code, until they arrive
            if now > pt[1]: self.punch_to.remove(pt); continue
            if now - pt[2] > 0.25: pt[2] = now; self.send(pt[0], {"t": "punch"})
        if now - self._ka_t > 5.0:                     # keep-alive: holds router + firewall mappings even when idle
            self._ka_t = now
            for p in self.peers.values(): self.send(p["addr"], {"t": "ka"})
        if now - self._ping_t > 1.0:
            self._ping_t = now
            for p in self.peers.values(): self.send(p["addr"], {"t": "ping", "c": now})
        if self.peers:
            sts = {"0": my_state} if my_state is not None else {}
            for k, p in self.peers.items():
                if p["state"] is not None: sts[str(k)] = p["state"]
            self.broadcast({"t": "sts", "s": sts})
        if now - self._roster_t > 2.0:
            self._roster_t = now
            ros = [{"id": 0, "name": self.name, "cfg": self.cfg, "ping": 0, "host": True}] + \
                  [{"id": k, "name": p["name"], "cfg": p["cfg"], "ping": p["ping"]} for k, p in self.peers.items()]
            self.broadcast({"t": "roster", "p": ros})
        if self.lan is not None and now - self._lan_t > 2.0:
            self._lan_t = now
            for dst in ("255.255.255.255", "127.255.255.255"):     # from the game socket: LAN replies count as responses
                try: self._tx(self._lan_pkt(), (dst, LAN_PORT))
                except OSError: pass

    def _lan_pkt(self):
        return seal(LAN_KEY, {"t": "lan", "code": self.code, "name": self.name, "pw": bool(self.password), "n": len(self.peers) + 1,
                              "ip": self.lip, "port": self.port})

    def _lan_reply(self, addr):
        try: self._tx(self._lan_pkt(), addr)
        except OSError: pass

    def _join_tick(self, now, my_state):
        if self.state == "joining":
            if now - self._hello_t > 0.4:
                self._hello_t = now
                self.send(self.host_addr, {"t": "probe"}, self.key0)
                self.send(self.host_addr, {"t": "hello", "name": self.name, "cfg": self.cfg, "v": VER})
            el = now - (self.join_started or now)
            if el > 4 and self.reachable and getattr(self, "need_pw", False): self.status = "HOST ANSWERED - CHECK THE PASSWORD"
            elif el > 5 and not self.reachable: self.status = "NO ANSWER YET - SEND THE HOST YOUR REPLY CODE (LET A FRIEND IN)"
            if el > 120:
                self.state = "error"
                self.status = ("WRONG PASSWORD" if self.reachable and getattr(self, "need_pw", False) else
                               "COULD NOT REACH THE HOST. " + self.forward_hint())
        elif self.state == "joined":
            if my_state is not None: self.send(self.host_addr, {"t": "st", "s": my_state})
            if now - self._ping_t > 1.0:
                self._ping_t = now; self.send(self.host_addr, {"t": "ping", "c": now})
            if now - self._ka_t > 5.0: self._ka_t = now; self.send(self.host_addr, {"t": "ka"})
            if now - getattr(self, "last_host", now) > 12.0:
                self.state = "ended"; self.status = "LOST CONNECTION TO THE HOST"; self.events.append(("ended", None))

    def update_profile(self, name, cfg):
        self.name, self.cfg = name, cfg
        if self.role == "join" and self.state == "joined": self.to_host({"t": "cfg", "name": name, "cfg": cfg})
        else: self._roster_t = 0.0

    def close(self):
        if self.role == "host":
            for p in self.peers.values():
                for _ in range(2): self.send(p["addr"], {"t": "end"})
        elif self.state == "joined":
            for _ in range(2): self.send(self.host_addr, {"t": "bye"})
        self.alive = False
        try: self.sock.close()
        except Exception: pass
        if self.lan is not None:
            try: self.lan.close()
            except Exception: pass
        if self.upnp is not None and self.upnp.mapped:
            threading.Thread(target=self.upnp.unmap, daemon=True).start()


class LanBrowser:
    """listens for SFC 27 sessions on the local network"""
    def __init__(self):
        self.found = {}; self.alive = True; self.s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if hasattr(socket, "SO_REUSEPORT"):
                try: s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
                except OSError: pass
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            s.bind(("", LAN_PORT)); s.settimeout(0.3); self.s = s
            threading.Thread(target=self._rx, daemon=True).start()
            threading.Thread(target=self._ask, daemon=True).start()
        except OSError:
            self.s = None

    def _rx(self):
        while self.alive:
            try: data, addr = self.s.recvfrom(4096)
            except socket.timeout: continue
            except OSError: break
            m = open_(LAN_KEY, data)
            if m and m.get("t") == "lan" and parse_code(m.get("code")):
                self.found[m["code"]] = dict(m, seen=time.time(), lan_addr=(addr[0], int(m.get("port", PORT))))

    def _ask(self):
        """outbound broadcast "anyone hosting?" - hosts answer straight back, which a stateful firewall lets in"""
        q = seal(LAN_KEY, {"t": "lanq"})
        while self.alive and self.s is not None:
            for dst in ("255.255.255.255", "127.255.255.255"):
                try: self.s.sendto(q, (dst, PORT))
                except OSError: pass
            time.sleep(1.0)

    def sessions(self):
        now = time.time()
        return [v for v in self.found.values() if now - v["seen"] < 7]

    def close(self):
        self.alive = False
        if self.s:
            try: self.s.close()
            except Exception: pass
