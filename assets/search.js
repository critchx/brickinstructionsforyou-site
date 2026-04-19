
let SEARCH_DATA=[];
fetch('/assets/search-index.json').then(r=>r.json()).then(d=>SEARCH_DATA=d).catch(()=>{});
const input=document.getElementById('site-search');
const dd=document.getElementById('search-dropdown');
function render(q){
  if(!q){dd.style.display='none';dd.innerHTML='';return;}
  const term=q.toLowerCase();
  const results=SEARCH_DATA.filter(x=>x.keywords.toLowerCase().includes(term)).slice(0,12);
  dd.innerHTML=results.map(r=>`<a class="search-item" href="${r.url}">${r.title}</a>`).join('');
  dd.style.display=results.length?'block':'none';
}
if(input){
 input.addEventListener('input',e=>render(e.target.value.trim()));
 input.addEventListener('keydown',e=>{if(e.key==='Enter'){const first=dd.querySelector('.search-item'); if(first){window.location=first.href;}}});
 document.addEventListener('click',e=>{if(dd && !dd.contains(e.target) && e.target!==input) dd.style.display='none';});
}
