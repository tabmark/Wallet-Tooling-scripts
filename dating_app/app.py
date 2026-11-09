"""Minimal dating app for single parents. Stdlib only: python3 app.py -> http://localhost:8000"""
import html, sqlite3, secrets
from http.server import BaseHTTPRequestHandler, HTTPServer
from http.cookies import SimpleCookie
from urllib.parse import parse_qs

db = sqlite3.connect("dating.db", check_same_thread=False)
db.executescript("""
CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY, name TEXT UNIQUE, password TEXT,
  role TEXT, kids INTEGER, city TEXT, bio TEXT, token TEXT);
CREATE TABLE IF NOT EXISTS likes(src INTEGER, dst INTEGER, PRIMARY KEY(src, dst));
CREATE TABLE IF NOT EXISTS messages(src INTEGER, dst INTEGER, body TEXT);
""")

e = lambda s: html.escape(str(s))
SIGNUP = """<h2>Sign up (18+ only)</h2><form method=post action=/signup>
Name <input name=name required> Password <input name=password type=password required><br>
I am a <select name=role><option>Baby Daddy</option><option>Baby Momma</option></select>
Kids <input name=kids type=number min=1 value=1> City <input name=city required><br>
Bio <textarea name=bio></textarea><br><label><input type=checkbox name=adult required> I am 18 or older</label>
<button>Sign up</button></form>
<h2>Log in</h2><form method=post action=/login>Name <input name=name> Password <input name=password type=password>
<button>Log in</button></form>"""


class H(BaseHTTPRequestHandler):
    def user(self):
        tok = SimpleCookie(self.headers.get("Cookie", "")).get("t")
        return tok and db.execute("SELECT * FROM users WHERE token=?", (tok.value,)).fetchone()

    def send(self, body, cookie=None, redirect=None):
        self.send_response(303 if redirect else 200)
        if cookie: self.send_header("Set-Cookie", f"t={cookie}; HttpOnly; Path=/")
        if redirect: self.send_header("Location", redirect)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(f"<title>CoParent Connect</title><h1>CoParent Connect</h1>{body}".encode())

    def do_GET(self):
        u = self.user()
        if self.path == "/logout": return self.send("", cookie="x", redirect="/")
        if not u: return self.send(SIGNUP)
        uid = u[0]
        if self.path.startswith("/chat/"):
            other = int(self.path.split("/")[2])
            if not self.matched(uid, other): return self.send("Not a match.")
            msgs = db.execute("SELECT u.name, m.body FROM messages m JOIN users u ON u.id=m.src WHERE "
                              "(src=? AND dst=?) OR (src=? AND dst=?)", (uid, other, other, uid)).fetchall()
            log = "".join(f"<p><b>{e(n)}:</b> {e(b)}</p>" for n, b in msgs)
            return self.send(f"<a href=/>Back</a>{log}<form method=post action=/msg/{other}>"
                             "<input name=body required><button>Send</button></form>")
        # Home: browse the other role, show matches
        want = "Baby Momma" if u[3] == "Baby Daddy" else "Baby Daddy"
        people = db.execute("SELECT id,name,kids,city,bio FROM users WHERE role=? AND id NOT IN "
                            "(SELECT dst FROM likes WHERE src=?)", (want, uid)).fetchall()
        matches = db.execute("SELECT u.id,u.name FROM likes a JOIN likes b ON a.dst=b.src AND b.dst=a.src "
                             "JOIN users u ON u.id=a.dst WHERE a.src=?", (uid,)).fetchall()
        cards = "".join(f"<div style='border:1px solid;margin:4px;padding:4px'><b>{e(n)}</b> ({e(k)} kids, {e(c)})"
                        f"<br>{e(b)}<form method=post action=/like/{i}><button>Like</button></form></div>"
                        for i, n, k, c, b in people) or "<p>No new profiles yet.</p>"
        mlist = "".join(f"<li><a href=/chat/{i}>{e(n)}</a></li>" for i, n in matches) or "<li>None yet</li>"
        self.send(f"<p>Hi {e(u[1])} ({e(u[3])}) | <a href=/logout>Log out</a></p>"
                  f"<h2>Matches</h2><ul>{mlist}</ul><h2>Browse {want}s</h2>{cards}")

    def matched(self, a, b):
        return db.execute("SELECT COUNT(*) FROM likes WHERE (src=? AND dst=?) OR (src=? AND dst=?)",
                          (a, b, b, a)).fetchone()[0] == 2

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        f = {k: v[0] for k, v in parse_qs(self.rfile.read(n).decode()).items()}
        if self.path == "/signup":
            tok = secrets.token_hex(16)
            try:
                db.execute("INSERT INTO users(name,password,role,kids,city,bio,token) VALUES(?,?,?,?,?,?,?)",
                           (f["name"], f["password"], f["role"], int(f.get("kids", 1)), f["city"], f.get("bio", ""), tok))
                db.commit()
            except sqlite3.IntegrityError:
                return self.send("Name taken. <a href=/>Back</a>")
            return self.send("", cookie=tok, redirect="/")
        if self.path == "/login":
            tok = secrets.token_hex(16)
            cur = db.execute("UPDATE users SET token=? WHERE name=? AND password=?",
                             (tok, f.get("name"), f.get("password")))
            db.commit()
            return self.send("", cookie=tok, redirect="/") if cur.rowcount else self.send("Bad login. <a href=/>Back</a>")
        u = self.user()
        if not u: return self.send("", redirect="/")
        other = int(self.path.split("/")[2])
        if self.path.startswith("/like/"):
            db.execute("INSERT OR IGNORE INTO likes VALUES(?,?)", (u[0], other))
        elif self.path.startswith("/msg/") and self.matched(u[0], other):
            db.execute("INSERT INTO messages VALUES(?,?,?)", (u[0], other, f.get("body", "")))
        db.commit()
        self.send("", redirect=f"/chat/{other}" if self.path.startswith("/msg/") else "/")


if __name__ == "__main__":
    print("Running on http://localhost:8000")
    HTTPServer(("", 8000), H).serve_forever()
