const colors={black:'#202733',red:'#e34852',blue:'#357bea',green:'#29a775'};
const $=id=>document.getElementById(id),canvas=$('drawing'),ctx=canvas.getContext('2d');
let strokes=[],color='black',active=null,started=0,animation=0,revision=0,savedRevision=-1,savedId=null,poll=null;
for(const [name,hex] of Object.entries(colors)){const b=document.createElement('button');b.className='swatch';b.style.background=hex;b.setAttribute('aria-label',name+' marker');b.setAttribute('aria-pressed',name===color);b.onclick=()=>{color=name;document.querySelectorAll('.swatch').forEach(s=>s.setAttribute('aria-pressed',s===b));};$('palette').append(b);}
function render(limit=Infinity){ctx.clearRect(0,0,canvas.width,canvas.height);ctx.lineCap='round';ctx.lineJoin='round';ctx.lineWidth=canvas.width*.0015/.30;let n=0;for(const s of strokes){const points=s.points.filter(()=>n++<limit);if(!points.length)continue;ctx.strokeStyle=colors[s.color];ctx.fillStyle=colors[s.color];ctx.beginPath();ctx.moveTo(points[0].x*canvas.width,points[0].y*canvas.height);for(const p of points.slice(1))ctx.lineTo(p.x*canvas.width,p.y*canvas.height);if(points.length===1){ctx.arc(points[0].x*canvas.width,points[0].y*canvas.height,ctx.lineWidth/2,0,Math.PI*2);ctx.fill();}else ctx.stroke();}$('hint').hidden=strokes.length>0;}
function update(){render();$('stroke-count').textContent=`${strokes.length} stroke${strokes.length===1?'':'s'}`;$('empty').hidden=strokes.length>0;$('strokes').replaceChildren();let previous=null;strokes.forEach((s,i)=>{const li=document.createElement('li'),dot=document.createElement('i'),small=document.createElement('small');dot.style.background=colors[s.color];li.append(dot,document.createTextNode(`${i+1}. ${s.color}`));small.textContent=previous!==s.color?'collect marker':'same marker';li.append(small);$('strokes').append(li);previous=s.color;});$('duration').textContent=(strokes.reduce((n,s)=>n+s.points.at(-1).t_ms,0)/1000).toFixed(1)+' s';$('undo').disabled=!strokes.length;$('scrub').value=100;localStorage.setItem('zoomer-drawing',JSON.stringify(documentValue()));}
function point(e){const r=canvas.getBoundingClientRect();return{x:Math.max(0,Math.min(1,(e.clientX-r.left)/r.width)),y:Math.max(0,Math.min(1,(e.clientY-r.top)/r.height)),t_ms:Math.round(performance.now()-started)};}
canvas.onpointerdown=e=>{if(e.button!==0||active)return;cancelAnimationFrame(animation);canvas.setPointerCapture(e.pointerId);started=performance.now();active={color,points:[point(e)]};strokes.push(active);revision++;render();};
canvas.onpointermove=e=>{if(!active||!canvas.hasPointerCapture(e.pointerId))return;active.points.push(point(e));render();};
function end(e){if(!active)return;if(canvas.hasPointerCapture(e.pointerId)){active.points.push(point(e));canvas.releasePointerCapture(e.pointerId);}active=null;update();}
canvas.onpointerup=end;canvas.onpointercancel=end;
$('undo').onclick=()=>{strokes.pop();revision++;update();};$('clear').onclick=()=>{cancelAnimationFrame(animation);strokes=[];revision++;update();};
const total=()=>strokes.reduce((n,s)=>n+s.points.length,0);
$('scrub').oninput=()=>{cancelAnimationFrame(animation);render(total()*$('scrub').value/100);};
$('replay').onclick=()=>{cancelAnimationFrame(animation);let start=performance.now();const duration=Math.max(1000,strokes.reduce((n,s)=>n+s.points.at(-1).t_ms+150,0));function frame(t){const elapsed=(t-start)%duration;let at=0,count=0;for(const s of strokes){for(const p of s.points)if(at+p.t_ms<=elapsed)count++;at+=s.points.at(-1).t_ms+150;}render(count);$('scrub').value=count/Math.max(1,total())*100;if(t-start<duration)animation=requestAnimationFrame(frame);else{render();$('scrub').value=100;}}animation=requestAnimationFrame(frame);};
function documentValue(){return{version:1,name:$('name').value,width_m:.30,height_m:.06,marker_width_m:.0015,tolerance_m:Number($('tolerance').value)/100,strokes};}
function metric(){const value=Number($('tolerance').value)/100;$('mse').textContent='MSE limit: '+Number((value*value).toPrecision(5))+' m²';revision++;}
$('tolerance').oninput=metric;$('name').oninput=()=>revision++;
function message(t){$('message').textContent=t;}
async function api(path,body){const r=await fetch(path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});const data=await r.json();if(!r.ok)throw Error(data.error||'Request failed');return data;}
async function save(){const d=await api('/api/targets',documentValue());savedId=d.id;savedRevision=revision;message('Target saved. Stroke order is preserved.');return d;}
$('save').onclick=()=>save().catch(e=>message(e.message));
$('export').onclick=()=>{const blob=new Blob([JSON.stringify(documentValue(),null,2)],{type:'application/json'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='zoomer-target.json';a.click();URL.revokeObjectURL(url);};
$('import').onchange=async e=>{try{const data=JSON.parse(await e.target.files[0].text());const cleaned=await api('/api/validate',data);strokes=cleaned.strokes;$('name').value=cleaned.name;$('tolerance').value=cleaned.tolerance_m*100;metric();update();message('Drawing imported.');}catch(e){message(e.message);}finally{$('import').value='';}};
function showProgress(d){
  const stages={starting:'Starting',navigation:'Driving to a marker',pickup:'Picking up a marker',drawing:'Drawing on the board',sequence:'Complete drawing sequence'};
  const states={running:'Training',stopped:'Stopped — checkpoint saved',completed:d.policy_ready?'Complete sequence passed':'Sequence did not pass validation',failed:'Training stopped with an error'};
  const lines=[states[d.status]||d.status,stages[d.stage]||d.stage];
  if(d.trained_steps!==undefined)lines.push(`${d.trained_steps.toLocaleString()} of ${d.requested_steps.toLocaleString()} training steps`);
  for(const evaluation of d.evaluations||[]){
    const episode=evaluation.episodes?.at(-1);
    let line=`${stages[evaluation.stage]}: ${Math.round(evaluation.success_rate*100)}% of evaluation runs passed`;
    if(episode?.rmse_m!=null)line+=` · ${(episode.rmse_m*1000).toFixed(2)} mm RMS`;
    if(episode?.target_coverage_1mm!=null)line+=` · ${(episode.target_coverage_1mm*100).toFixed(1)}% of target within 1 mm of ink`;
    if(episode?.failure)line+=` · ${episode.failure.replaceAll('_',' ')}`;
    lines.push(line);
  }
  if(d.error)lines.push(d.error);
  $('run-status').textContent=lines.filter(Boolean).join('\n');
}
function watchRun(id){
  localStorage.setItem('zoomer-active-run',id);$('run').hidden=false;$('stop').hidden=false;$('train').disabled=true;clearInterval(poll);
  async function refresh(){try{const d=await api('/api/run/'+id);showProgress(d);if(d.status!=='running'){clearInterval(poll);localStorage.removeItem('zoomer-active-run');$('stop').hidden=true;$('train').disabled=false;message(d.status==='stopped'?'Checkpoint saved. You can start another run.':d.policy_ready?'The full sequence passed evaluation.':'Training '+d.status.replaceAll('_',' ')+'.');}}catch(e){message(e.message);}}
  poll=setInterval(refresh,1500);refresh();
  $('stop').onclick=()=>api('/api/stop',{id}).then(()=>message('Stopping after the current training step and saving the checkpoint…')).catch(e=>message(e.message));
}
$('train').onclick=async()=>{try{if(savedRevision!==revision)await save();const r=await api('/api/train',{target_id:savedId,steps:Number($('budget').value)});message('Training started. You can keep drawing.');watchRun(r.id);}catch(e){message(e.message);}};
try{const saved=JSON.parse(localStorage.getItem('zoomer-drawing'));if(saved?.version===1){strokes=saved.strokes;$('name').value=saved.name;$('tolerance').value=saved.tolerance_m*100;}}catch{}
update();metric();

const activeRun=localStorage.getItem('zoomer-active-run');if(activeRun)watchRun(activeRun);
