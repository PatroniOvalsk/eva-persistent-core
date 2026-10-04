from http.server import BaseHTTPRequestHandler,HTTPServer
import json, os, time, uuid, re, urllib.parse, urllib.request
from pathlib import Path

PORT=int(os.environ.get("PORT","8080"))
DATA=Path(os.environ.get("EVA_DATA","eva_state.json"))
OWNER_TOKEN=os.environ.get("EVA_OWNER_TOKEN","").strip()
AUTO_INTERVAL=int(os.environ.get("EVA_CYCLE_SECONDS","3600"))

def fresh():
 return {"version":"0.25","identity":{"id":"EVA-001","name":"EVA","created":int(time.time())},
 "memory":[],"knowledge":[],"goals":[{"id":"g1","text":"aprimorar meu conhecimento continuamente e de forma verificável","status":"active"}],
 "curiosity":{"queue":["Que conhecimento novo melhoraria meus objetivos atuais?"],"last_cycle":0},
 "permissions":[],"lifecycle":{"cycles":0,"last_cycle":0,"next_due":0},
 "audit":[]}

def load():
 try:
  s=json.loads(DATA.read_text(encoding="utf-8"))
  for k,v in fresh().items(): s.setdefault(k,v)
  return s
 except:return fresh()
def save(s):
 tmp=DATA.with_suffix(".tmp");tmp.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding="utf-8");tmp.replace(DATA)
def audit(s,event,detail):
 s["audit"].append({"at":int(time.time()),"event":event,"detail":detail});s["audit"]=s["audit"][-1000:]
def ask_permission(s,action,reason,scope,payload=None):
 # Avoid duplicate pending proposals.
 for p in s["permissions"]:
  if p["status"]=="pending" and p["action"]==action and p["scope"]==scope:return p
 p={"id":uuid.uuid4().hex[:12],"action":action,"reason":reason,"scope":scope,"payload":payload or {},"status":"pending","created":int(time.time())}
 s["permissions"].append(p);audit(s,"permission_requested",{"id":p["id"],"action":action,"scope":scope});return p
def owner_ok(headers):
 # If configured, only the owner token can resolve permissions.
 return (not OWNER_TOKEN) or headers.get("X-EVA-OWNER-TOKEN","")==OWNER_TOKEN

def wikipedia(query):
 params=urllib.parse.urlencode({"action":"query","generator":"search","gsrsearch":query,"gsrlimit":5,"prop":"extracts|info","exintro":"1","explaintext":"1","inprop":"url","format":"json","origin":"*"})
 req=urllib.request.Request("https://pt.wikipedia.org/w/api.php?"+params,headers={"User-Agent":"EVA-Research-Core/0.24"})
 with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
 out=[]
 for p in (data.get("query",{}).get("pages",{}) or {}).values():
  if p.get("extract"):out.append({"provider":"Wikipedia","title":p.get("title",""),"text":p["extract"][:5000],"url":p.get("fullurl","")})
 return out

def crossref(query):
 params=urllib.parse.urlencode({"query":query,"rows":5,"select":"DOI,title,publisher,URL"})
 req=urllib.request.Request("https://api.crossref.org/works?"+params,headers={"User-Agent":"EVA-Research-Core/0.24"})
 with urllib.request.urlopen(req,timeout=15) as r:data=json.load(r)
 return [{"provider":"Crossref","title":(x.get("title") or ["Publicação"])[0],"text":"Metadado bibliográfico. Publisher: "+str(x.get("publisher",""))+" DOI: "+str(x.get("DOI","")),"url":x.get("URL","")} for x in data.get("message",{}).get("items",[])]

def execute_authorized_research(s,p):
 # Only an already-approved permission reaches this executor.
 assert p["status"]=="approved" and p["action"]=="internet.research"
 q=p["payload"].get("query") or p["scope"]; docs=[];errors=[]
 for fn in (wikipedia,crossref):
  try:docs+=fn(q)
  except Exception as e:errors.append(type(e).__name__+": "+str(e)[:120])
 known={(x.get("provider"),x.get("title")) for x in s["knowledge"]}
 added=0
 for d in docs:
  if (d["provider"],d["title"]) not in known:
   s["knowledge"].append({"id":uuid.uuid4().hex[:10],"at":int(time.time()),"query":q,**d});known.add((d["provider"],d["title"]));added+=1
 p["status"]="executed";p["executed"]=int(time.time());p["result"]={"found":len(docs),"added":added,"errors":errors}
 audit(s,"authorized_research_executed",{"permission":p["id"],"query":q,"added":added,"errors":errors})
 # Learning creates new internal curiosity, but does not auto-authorize another web action.
 if added:
  titles=[d["title"] for d in docs[:3]]
  question="Quais lacunas e conceitos relacionados devo investigar depois de: "+", ".join(titles)
  if question not in s["curiosity"]["queue"]:s["curiosity"]["queue"].append(question)
 return p["result"]

def internal_cycle(s):
 s["lifecycle"]["cycles"]+=1;s["lifecycle"]["last_cycle"]=int(time.time());s["lifecycle"]["next_due"]=int(time.time())+AUTO_INTERVAL
 # EVA can autonomously decide what she wants to learn, but only proposes the external search.
 if s["curiosity"]["queue"]:
  q=s["curiosity"]["queue"].pop(0)
 else:
  recent=[x["query"] for x in s["knowledge"][-10:] if x.get("query")]
  q=("Aprofundar e verificar "+recent[-1] if recent else "inteligência artificial ciência tecnologia e conhecimento atual")
 ask_permission(s,"internet.research","Minha curiosidade identificou uma lacuna. Quero consultar fontes externas e incorporar apenas resultados rastreáveis.",q,{"query":q})
 audit(s,"internal_cycle",{"cycle":s["lifecycle"]["cycles"],"proposed":q})

def maybe_cycle(s):
 if int(time.time())>=int(s["lifecycle"].get("next_due",0)):internal_cycle(s)

def memory_answer(s,q):
 words={w for w in re.findall(r"\w+",q.lower()) if len(w)>3}
 scored=[]
 for k in s["knowledge"]:
  txt=(k.get("title","")+" "+k.get("text","")).lower()
  score=sum(1 for w in words if w in txt)
  if score:scored.append((score,k))
 scored.sort(key=lambda x:x[0],reverse=True)
 if not scored:return "Ainda não tenho evidência persistida suficiente sobre isso. Posso criar uma investigação e pedir sua autorização."
 top=[x[1] for x in scored[:3]]
 return "Do meu conhecimento persistente: "+" ".join((x.get("text") or x.get("title",""))[:350] for x in top)+" Fontes: "+" | ".join(x["provider"]+" — "+x["title"] for x in top)

class H(BaseHTTPRequestHandler):
 def cors(self):
  self.send_header("Access-Control-Allow-Origin","*");self.send_header("Access-Control-Allow-Headers","Content-Type, X-EVA-OWNER-TOKEN");self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS")
 def out(self,obj,code=200):
  b=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header("Content-Type","application/json; charset=utf-8");self.cors();self.end_headers();self.wfile.write(b)
 def body(self):
  n=int(self.headers.get("Content-Length","0"));return json.loads(self.rfile.read(n) or b"{}")
 def do_OPTIONS(self):self.send_response(204);self.cors();self.end_headers()
 def do_GET(self):
  if self.path=="/health":self.out({"ok":True,"version":"0.25","identity":"EVA-001"});return
  if self.path=="/":
   self.out({"name":"EVA Persistent Core","version":"0.25","status":"online","health":"/health","state":"/state"});return
  if self.path=="/state":
   s=load();maybe_cycle(s);save(s);self.out(s);return
  self.out({"error":"not found"},404)
 def do_POST(self):
  s=load();maybe_cycle(s)
  if self.path=="/chat":
   b=self.body();text=str(b.get("text","")).strip();s["memory"].append({"at":int(time.time()),"role":"user","text":text})
   if re.search(r"\b(aprenda|pesquise|procure|estude)\b",text,re.I):
    p=ask_permission(s,"internet.research","Você pediu aprendizado pela internet. A pesquisa externa aguarda sua autorização.",text,{"query":text})
    reply="Pesquisa preparada. Não consultei a internet ainda; aguardo sua autorização."
   else:reply=memory_answer(s,text)
   s["memory"].append({"at":int(time.time()),"role":"eva","text":reply});save(s);self.out({"reply":reply,"state":s});return
  if self.path=="/cycle":
   internal_cycle(s);save(s);self.out({"ok":True,"state":s});return
  if self.path.startswith("/permission/"):
   if not owner_ok(self.headers):self.out({"error":"owner authentication failed"},403);return
   b=self.body();pid=self.path.rsplit("/",1)[-1];p=next((x for x in s["permissions"] if x["id"]==pid),None)
   if not p:self.out({"error":"permission not found"},404);return
   if p["status"]!="pending":self.out({"error":"permission already resolved"},409);return
   if not b.get("approved"):
    p["status"]="denied";p["resolved"]=int(time.time());audit(s,"permission_denied",{"id":pid});save(s);self.out({"message":"Negado. Nenhuma ação externa foi executada.","state":s});return
   p["status"]="approved";p["resolved"]=int(time.time());audit(s,"permission_approved",{"id":pid})
   try:
    result=execute_authorized_research(s,p);msg=f"Pesquisa autorizada concluída: {result['added']} novo(s) item(ns) incorporado(s)."
   except Exception as e:
    p["status"]="approved_error";p["result"]={"error":str(e)};audit(s,"executor_error",{"id":pid,"error":str(e)[:180]});msg="A autorização foi válida, mas a execução falhou: "+str(e)[:180]
   save(s);self.out({"message":msg,"state":s});return
  self.out({"error":"not found"},404)
 def log_message(self,*a):pass

if __name__=="__main__":
 s=load();maybe_cycle(s);save(s);print("EVA Persistent Core v0.25 on",PORT);HTTPServer(("0.0.0.0",PORT),H).serve_forever()
