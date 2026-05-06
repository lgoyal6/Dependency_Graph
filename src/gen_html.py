"""Generates index.html with embedded vis.js and graph data."""
import json
from pathlib import Path

root = Path(__file__).parent.parent

with open(root / "dependency_graph.json") as f:
    graph_data = f.read()

with open(root / "vis-network.min.js") as f:
    vis_js = f.read()

# Escape </script> inside JS to avoid breaking HTML parser
vis_js = vis_js.replace("</script>", "<\\/script>")

html = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Composio Tool Dependency Graph</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%}
body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#0f1117;color:#e2e8f0;display:flex;flex-direction:column;height:100vh;overflow:hidden}
header{flex-shrink:0;padding:8px 14px;background:#1a1d27;border-bottom:1px solid #2d3148;display:flex;align-items:center;gap:10px;flex-wrap:wrap}
header h1{font-size:14px;font-weight:700;color:#fff;white-space:nowrap}
.ctrl{display:flex;gap:7px;flex-wrap:wrap;align-items:center;flex:1}
.ctrl input{padding:5px 9px;background:#262a3a;border:1px solid #3d4258;border-radius:5px;color:#e2e8f0;font-size:12px;width:170px;outline:none}
.ctrl input:focus{border-color:#6366f1}
.fb{padding:3px 9px;border-radius:5px;border:1px solid transparent;cursor:pointer;font-size:11px;font-weight:600;opacity:.4;transition:opacity .15s;white-space:nowrap}
.fb.on{opacity:1}
.fb:hover{opacity:.85}
.sep{width:1px;height:18px;background:#2d3148;flex-shrink:0}
#stats{font-size:11px;color:#94a3b8;white-space:nowrap;margin-left:auto}
#wrap{flex:1;min-height:0;position:relative}
#net{width:100%;height:100%}
#ov{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;background:#0f1117;gap:10px;font-size:13px;color:#64748b}
.spin{width:34px;height:34px;border:3px solid #2d3148;border-top-color:#6366f1;border-radius:50%;animation:sp .8s linear infinite}
@keyframes sp{to{transform:rotate(360deg)}}
#tip{position:fixed;background:#1e2235;border:1px solid #3d4258;border-radius:8px;padding:10px 13px;font-size:12px;max-width:340px;z-index:999;pointer-events:none;display:none;box-shadow:0 8px 32px rgba(0,0,0,.5)}
#tip .tn{font-weight:700;color:#fff;margin-bottom:2px}
#tip .ts{font-family:monospace;font-size:10px;color:#6366f1;margin-bottom:4px}
#tip .td{color:#94a3b8;line-height:1.4;font-size:11px}
#tip .ti{margin-top:5px;font-size:11px;color:#64748b}
#tip .ti strong{color:#94a3b8}
#tip .badge{display:inline-block;padding:1px 5px;border-radius:3px;font-size:10px;font-weight:600;margin-left:4px}
#pathbar{display:none;padding:6px 14px;background:#1a1d27;border-top:1px solid #2d3148;font-size:12px;color:#94a3b8;align-items:center;gap:8px}
#pathbar.show{display:flex}
#pathbar button{padding:2px 8px;background:#262a3a;border:1px solid #3d4258;border-radius:4px;color:#e2e8f0;cursor:pointer;font-size:11px}
#pathbar button:hover{background:#3d4258}
footer{flex-shrink:0;display:flex;flex-wrap:wrap;gap:5px;padding:5px 12px;background:#1a1d27;border-top:1px solid #2d3148;font-size:10px}
.li{display:flex;align-items:center;gap:4px;color:#94a3b8}
.dot{width:8px;height:8px;border-radius:50%}
.legend-section{display:flex;align-items:center;gap:5px;padding-right:10px;border-right:1px solid #2d3148}
</style>
</head>
<body>
<header>
  <h1>Composio Dependency Graph</h1>
  <div class="ctrl">
    <input type="text" id="search" placeholder="Search tools..." oninput="doSearch()"/>
    <div class="sep"></div>
    <button class="fb on" style="background:#374151;color:#e2e8f0;border-color:#4b5563" onclick="flt('all',this)">All</button>
    <button class="fb"    style="background:#1e3a5f;color:#60a5fa;border-color:#3b82f6" onclick="flt('googlesuper',this)">Google Super</button>
    <button class="fb"    style="background:#1a2e1a;color:#4ade80;border-color:#22c55e" onclick="flt('github',this)">GitHub</button>
    <button class="fb"    style="background:#3b1919;color:#f87171;border-color:#ef4444" onclick="flt('gmail',this)">Gmail</button>
    <button class="fb"    style="background:#1e2d4a;color:#93c5fd;border-color:#60a5fa" onclick="flt('calendar',this)">Calendar</button>
    <button class="fb"    style="background:#2d2514;color:#fbbf24;border-color:#f59e0b" onclick="flt('github_issues',this)">Issues</button>
    <button class="fb"    style="background:#2a1a3e;color:#c084fc;border-color:#a855f7" onclick="flt('github_prs',this)">Pull Requests</button>
    <button class="fb"    style="background:#1a2e2a;color:#34d399;border-color:#10b981" onclick="flt('github_repos',this)">Repos</button>
    <button class="fb"    style="background:#1e2a1e;color:#86efac;border-color:#22c55e" onclick="flt('github_actions',this)">Actions</button>
    <div class="sep"></div>
    <button class="fb on" id="btnReq"  style="background:#1e3048;color:#60a5fa;border-color:#3b82f6"  onclick="toggleEdge('required',this)">Required</button>
    <button class="fb on" id="btnOpt"  style="background:#2a2a1a;color:#fbbf24;border-color:#d97706"  onclick="toggleEdge('optional',this)">Optional</button>
    <button class="fb on" id="btnSem"  style="background:#2a1a2a;color:#c084fc;border-color:#9333ea"  onclick="toggleEdge('semantic',this)">Semantic</button>
    <div class="sep"></div>
    <button class="fb" id="btnHier" style="background:#1a2e2a;color:#34d399;border-color:#10b981" onclick="toggleLayout()">Hierarchical</button>
    <button class="fb" id="btnPath" style="background:#262a3a;color:#e2e8f0;border-color:#4b5563" onclick="togglePathMode()">Path Finder</button>
  </div>
  <span id="stats">Loading...</span>
</header>
<div id="wrap">
  <div id="net"></div>
  <div id="ov"><div class="spin"></div><div id="ovtxt">Building graph...</div></div>
</div>
<div id="pathbar">
  <span id="pathmsg">Click two nodes to find the shortest dependency path between them</span>
  <button onclick="clearPath()">Clear</button>
  <button onclick="togglePathMode()">Exit</button>
</div>
<div id="tip"></div>
<footer id="legend">
  <div class="legend-section">
    <div class="li"><div class="dot" style="background:#fff;border:2px solid #ffd700"></div>Entry point (no prereqs)</div>
    <div class="li"><div class="dot" style="background:#fff;border:2px solid #ff6b6b"></div>Terminal action</div>
  </div>
  <div class="legend-section">
    <div class="li"><div style="width:20px;height:2px;background:#3b82f6"></div>Required dependency</div>
    <div class="li"><div style="width:20px;height:1px;background:#d97706;border-top:1px dashed #d97706"></div>Optional</div>
    <div class="li"><div style="width:20px;height:1px;background:#9333ea;border-top:1px dotted #9333ea"></div>Semantic</div>
  </div>
</footer>

<script>""" + vis_js + """</script>
<script>
const RAW=""" + graph_data + """;

const COLORS={
  gmail:{bg:"#ef4444",bd:"#dc2626",tx:"#fff"},
  calendar:{bg:"#3b82f6",bd:"#2563eb",tx:"#fff"},
  drive:{bg:"#f59e0b",bd:"#d97706",tx:"#fff"},
  sheets:{bg:"#10b981",bd:"#059669",tx:"#fff"},
  docs:{bg:"#06b6d4",bd:"#0891b2",tx:"#fff"},
  slides:{bg:"#8b5cf6",bd:"#7c3aed",tx:"#fff"},
  maps:{bg:"#ec4899",bd:"#db2777",tx:"#fff"},
  contacts:{bg:"#14b8a6",bd:"#0d9488",tx:"#fff"},
  photos:{bg:"#f97316",bd:"#ea580c",tx:"#fff"},
  googlesuper_other:{bg:"#6366f1",bd:"#4f46e5",tx:"#fff"},
  github_issues:{bg:"#f59e0b",bd:"#d97706",tx:"#fff"},
  github_prs:{bg:"#a855f7",bd:"#9333ea",tx:"#fff"},
  github_repos:{bg:"#22c55e",bd:"#16a34a",tx:"#fff"},
  github_actions:{bg:"#4ade80",bd:"#22c55e",tx:"#111"},
  github_orgs:{bg:"#2dd4bf",bd:"#14b8a6",tx:"#111"},
  github_users:{bg:"#60a5fa",bd:"#3b82f6",tx:"#fff"},
  github_checks:{bg:"#fb923c",bd:"#f97316",tx:"#fff"},
  github_webhooks:{bg:"#f472b6",bd:"#ec4899",tx:"#fff"},
  github_projects:{bg:"#818cf8",bd:"#6366f1",tx:"#fff"},
  github_packages:{bg:"#a78bfa",bd:"#8b5cf6",tx:"#fff"},
  github_other:{bg:"#475569",bd:"#334155",tx:"#fff"},
};
const LABELS={
  gmail:"Gmail",calendar:"Calendar",drive:"Drive",sheets:"Sheets",
  docs:"Docs",slides:"Slides",maps:"Maps",contacts:"Contacts",photos:"Photos",
  googlesuper_other:"Google (other)",github_issues:"Issues",github_prs:"Pull Requests",
  github_repos:"Repos",github_actions:"Actions/CI",github_orgs:"Orgs/Teams",
  github_users:"Users",github_checks:"Checks",github_webhooks:"Webhooks",
  github_projects:"Projects",github_packages:"Packages",github_other:"GitHub (other)",
};

let net, vN, vE, curFilter="all";
let incoming={}, outgoing={};
let showEdge={required:true,optional:true,semantic:true};
let hierMode=false;
let pathMode=false, pathSel=[];
let activeNodes=null; // for path highlight

// Build adjacency
RAW.edges.forEach(e=>{
  if(!outgoing[e.from])outgoing[e.from]=[];
  if(!incoming[e.to])incoming[e.to]=[];
  outgoing[e.from].push({slug:e.to,param:e.param,type:e.type});
  incoming[e.to].push({slug:e.from,param:e.param,type:e.type});
});

// Build legend
const leg=document.getElementById("legend");
[...new Set(RAW.nodes.map(n=>n.group))].sort().forEach(g=>{
  const c=COLORS[g]||{bg:"#94a3b8"};
  leg.innerHTML+=`<div class="li"><div class="dot" style="background:${c.bg}"></div>${LABELS[g]||g}</div>`;
});

function mkNodes(nodes){
  return nodes.map(n=>{
    const c=COLORS[n.group]||{bg:"#94a3b8",bd:"#64748b",tx:"#fff"};
    const indeg=(incoming[n.id]||[]).length, outdeg=(outgoing[n.id]||[]).length;
    const sz=Math.max(8,Math.min(28,8+(indeg+outdeg)*0.7));
    const lbl=n.label.length>22?n.label.slice(0,20)+"…":n.label;

    // Entry points: gold border; Terminal: red border; both: thicker
    let borderColor=c.bd, borderWidth=1.5, shape="dot";
    if(n.is_entry && n.is_terminal){borderColor="#ff6b6b";borderWidth=3;}
    else if(n.is_entry){borderColor="#ffd700";borderWidth=3;}
    else if(n.is_terminal){borderColor="#ff6b6b";borderWidth=2.5;}

    return{
      id:n.id, label:lbl,
      color:{background:c.bg,border:borderColor,highlight:{background:c.bg,border:"#fff"}},
      font:{color:c.tx,size:10},
      size:sz, shape, borderWidth,
      _raw:n,
      level: n.depth||0,
    };
  });
}

function edgeStyle(e){
  const isReq=e.type==="required", isOpt=e.type==="optional", isSem=e.type==="semantic";
  const color=isReq?"#3b82f6":isOpt?"#d97706":"#9333ea";
  const dashes=isReq?false:isOpt?[4,4]:[2,6];
  return{
    id:e.from+"->"+e.to, from:e.from, to:e.to,
    label:e.param==="semantic"?"":e.param,
    font:{size:8,color:"#475569",align:"middle"},
    color:{color,highlight:"#fff",hover:"#fff"},
    arrows:{to:{enabled:true,scaleFactor:0.5}},
    width:isReq?1.5:1, dashes,
    smooth:{type:"curvedCW",roundness:0.12},
    _type:e.type,
  };
}

function mkEdges(edges,nodeSet){
  return edges
    .filter(e=>nodeSet.has(e.from)&&nodeSet.has(e.to)&&showEdge[e.type||"required"])
    .map(e=>edgeStyle(e));
}

function getOptions(){
  if(hierMode){
    return{
      physics:{enabled:false},
      layout:{hierarchical:{direction:"LR",sortMethod:"directed",levelSeparation:200,nodeSpacing:60,treeSpacing:100}},
      interaction:{hover:true,hideEdgesOnDrag:false,tooltipDelay:200},
    };
  }
  return{
    physics:{
      enabled:true,solver:"forceAtlas2Based",
      forceAtlas2Based:{gravitationalConstant:-60,centralGravity:0.01,springLength:130,springConstant:0.08,damping:0.9,avoidOverlap:0.4},
      stabilization:{iterations:80,fit:true}
    },
    interaction:{hover:true,hideEdgesOnDrag:true,tooltipDelay:200},
  };
}

function draw(nodes,edges){
  const container=document.getElementById("net");
  const nodeSet=new Set(nodes.map(n=>n.id));
  vN=new vis.DataSet(mkNodes(nodes));
  vE=new vis.DataSet(mkEdges(edges,nodeSet));
  net=new vis.Network(container,{nodes:vN,edges:vE},getOptions());

  net.on("stabilizationProgress",p=>{
    document.getElementById("ovtxt").textContent="Stabilizing... "+Math.round(p.iterations/p.total*100)+"%";
  });
  net.on("stabilizationIterationsDone",()=>{
    hide();
    document.getElementById("stats").textContent=
      nodes.length+" tools · "+edges.filter(e=>showEdge[e.type||"required"]).length+" deps";
    net.fit();
  });
  // For hierarchical (physics off), hide immediately
  if(hierMode){hide(); document.getElementById("stats").textContent=nodes.length+" tools";}

  net.on("hoverNode",showTip);
  net.on("blurNode",()=>{document.getElementById("tip").style.display="none";});
  net.on("click",handleClick);
}

function hide(){document.getElementById("ov").style.display="none";}
function showLoading(msg){
  const ov=document.getElementById("ov");
  ov.style.display="flex";
  document.getElementById("ovtxt").textContent=msg||"Loading...";
}

function showTip(params){
  if(pathMode)return;
  const nid=params.node;
  const n=RAW.nodes.find(x=>x.id===nid);if(!n)return;
  const inc=(incoming[nid]||[]).slice(0,5);
  const out=(outgoing[nid]||[]).slice(0,5);
  const incT=(incoming[nid]||[]).length, outT=(outgoing[nid]||[]).length;

  const depthBadge=`<span class="badge" style="background:#1e3048;color:#60a5fa">depth ${n.depth||0}</span>`;
  const entryBadge=n.is_entry?`<span class="badge" style="background:#3d3000;color:#ffd700">entry point</span>`:"";
  const termBadge=n.is_terminal?`<span class="badge" style="background:#3d0000;color:#ff6b6b">terminal</span>`:"";

  const tip=document.getElementById("tip");
  tip.innerHTML=`
    <div class="tn">${n.label}${depthBadge}${entryBadge}${termBadge}</div>
    <div class="ts">${n.id}</div>
    <div class="td">${n.description||""}</div>
    <div class="ti"><strong>Needs (${incT}):</strong> ${incT===0?"<em>none — entry point</em>":inc.map(e=>`<code style="color:#6366f1">${e.slug.replace(/^(GOOGLESUPER|GITHUB)_/,"")}</code> [${e.param}]`).join(", ")+(incT>5?"…":"")}</div>
    <div class="ti"><strong>Enables (${outT}):</strong> ${outT===0?"<em>nothing — terminal</em>":out.map(e=>`<code style="color:#34d399">${e.slug.replace(/^(GOOGLESUPER|GITHUB)_/,"")}</code>`).join(", ")+(outT>5?"…":"")}</div>
  `;
  const dom=net.canvasToDOM({x:params.event.center.x,y:params.event.center.y});
  const rect=document.getElementById("net").getBoundingClientRect();
  let x=rect.left+dom.x+16, y=rect.top+dom.y-12;
  if(x+350>window.innerWidth)x-=366;
  if(y+220>window.innerHeight)y-=220;
  tip.style.left=x+"px";tip.style.top=y+"px";tip.style.display="block";
}

// ─── Path Finder ─────────────────────────────────────────────────────────────

function togglePathMode(){
  pathMode=!pathMode;
  pathSel=[];
  clearPathHighlight();
  const bar=document.getElementById("pathbar");
  const btn=document.getElementById("btnPath");
  if(pathMode){
    bar.classList.add("show");
    btn.classList.add("on");
    document.getElementById("pathmsg").textContent="Click a START node";
  } else {
    bar.classList.remove("show");
    btn.classList.remove("on");
    document.getElementById("pathmsg").textContent="Click two nodes to find the shortest dependency path between them";
  }
}

function handleClick(params){
  if(!pathMode)return;
  if(!params.nodes.length)return;
  const nid=params.nodes[0];

  if(pathSel.length===0){
    pathSel=[nid];
    highlightNode(nid,"#ffd700");
    document.getElementById("pathmsg").textContent=`Start: ${nid.replace(/^(GOOGLESUPER|GITHUB)_/,"")} — now click END node`;
  } else if(pathSel.length===1 && nid!==pathSel[0]){
    pathSel.push(nid);
    const path=bfsPath(pathSel[0],pathSel[1]);
    if(path){
      showPath(path);
      const hops=path.length-1;
      document.getElementById("pathmsg").textContent=`Path found: ${hops} hop${hops===1?"":"s"} — ${path.map(s=>s.replace(/^(GOOGLESUPER|GITHUB)_/,"")).join(" → ")}`;
    } else {
      document.getElementById("pathmsg").textContent=`No path found from ${pathSel[0].replace(/^(GOOGLESUPER|GITHUB)_/,"")} to ${nid.replace(/^(GOOGLESUPER|GITHUB)_/,"")}`;
      clearPathHighlight();
      pathSel=[];
    }
  }
}

function bfsPath(start,end){
  const prev={};
  const visited=new Set([start]);
  const q=[start];
  while(q.length){
    const cur=q.shift();
    if(cur===end){
      const path=[];
      let n=end;
      while(n!==undefined){path.unshift(n);n=prev[n];}
      return path;
    }
    for(const {slug} of (outgoing[cur]||[])){
      if(!visited.has(slug)&&vN.get(slug)){
        visited.add(slug);prev[slug]=cur;q.push(slug);
      }
    }
  }
  return null;
}

function showPath(path){
  clearPathHighlight();
  const pathSet=new Set(path);
  const pathEdges=new Set();
  for(let i=0;i<path.length-1;i++) pathEdges.add(path[i]+"->"+path[i+1]);

  vN.forEach(n=>{
    const inPath=pathSet.has(n.id);
    vN.update({id:n.id,opacity:inPath?1:0.1,
      color:{...n.color,border:n.id===path[0]?"#ffd700":n.id===path[path.length-1]?"#ff6b6b":n.color.border}});
  });
  vE.forEach(e=>{
    vE.update({id:e.id,color:{color:pathEdges.has(e.id)?"#fff":"#1a1a2e"},width:pathEdges.has(e.id)?3:0.5});
  });
}

function clearPath(){
  pathSel=[];
  clearPathHighlight();
  document.getElementById("pathmsg").textContent="Click a START node";
}

function clearPathHighlight(){
  vN&&vN.forEach(n=>vN.update({id:n.id,opacity:1}));
  vE&&vE.forEach(e=>vE.update({id:e.id,
    color:{color:e._type==="required"?"#3b82f6":e._type==="optional"?"#d97706":"#9333ea"},
    width:e._type==="required"?1.5:1}));
}

function highlightNode(id,color){
  const n=vN.get(id);
  if(n)vN.update({id,color:{...n.color,border:color},borderWidth:3});
}

// ─── Layout toggle ────────────────────────────────────────────────────────────

function toggleLayout(){
  hierMode=!hierMode;
  const btn=document.getElementById("btnHier");
  btn.classList.toggle("on",hierMode);
  redraw();
}

// ─── Edge type toggle ─────────────────────────────────────────────────────────

function toggleEdge(type,btn){
  showEdge[type]=!showEdge[type];
  btn.classList.toggle("on",showEdge[type]);
  redraw();
}

// ─── Filter + search ──────────────────────────────────────────────────────────

function flt(f,btn){
  curFilter=f;
  document.querySelectorAll(".fb").forEach(b=>{
    if(["all","googlesuper","github","gmail","calendar","github_issues","github_prs","github_repos","github_actions"].includes(b.dataset.f||b.textContent.toLowerCase().replace(/ /g,"_"))){
      b.classList.remove("on");
    }
  });
  btn.classList.add("on");
  redraw();
}

function doSearch(){redraw();}

function redraw(){
  const q=document.getElementById("search").value.toLowerCase();
  let nodes=RAW.nodes;
  let edges=RAW.edges;

  if(curFilter==="googlesuper")nodes=nodes.filter(n=>n.toolkit==="googlesuper");
  else if(curFilter==="github")nodes=nodes.filter(n=>n.toolkit==="github");
  else if(curFilter!=="all")nodes=nodes.filter(n=>n.group===curFilter);

  if(q){
    const hit=new Set();
    nodes.forEach(n=>{
      if(n.id.toLowerCase().includes(q)||n.label.toLowerCase().includes(q)){
        hit.add(n.id);
        RAW.edges.forEach(e=>{if(e.from===n.id)hit.add(e.to);if(e.to===n.id)hit.add(e.from);});
      }
    });
    nodes=RAW.nodes.filter(n=>hit.has(n.id));
  }

  const nodeSet=new Set(nodes.map(n=>n.id));
  edges=RAW.edges.filter(e=>nodeSet.has(e.from)&&nodeSet.has(e.to)&&showEdge[e.type||"required"]);

  showLoading("Updating...");
  vN.clear(); vE.clear();
  vN.add(mkNodes(nodes));
  vE.add(mkEdges(RAW.edges.filter(e=>nodeSet.has(e.from)&&nodeSet.has(e.to)),nodeSet));

  if(hierMode){
    hide();
    document.getElementById("stats").textContent=nodes.length+" tools";
  } else {
    net.once("stabilizationIterationsDone",()=>{
      hide();
      document.getElementById("stats").textContent=nodes.length+" tools · "+edges.length+" deps";
      net.fit();
    });
    net.stabilize(80);
  }
}

// ─── Init ─────────────────────────────────────────────────────────────────────

draw(RAW.nodes, RAW.edges);
</script>
</body>
</html>"""

with open(root / "index.html", "w") as f:
    f.write(html)
print(f"Written index.html ({len(html)//1024}KB)")
