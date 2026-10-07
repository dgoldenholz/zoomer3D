(() => {
  'use strict';
  const colors = {black:'#202733',red:'#e34852',blue:'#357bea',green:'#29a775'};
  const $ = name => document.getElementById('studio-'+name);
  const canvas = $('canvas'), ctx = canvas.getContext('2d');
  const storageKey = 'zoomer3d-whiteboard-draft-v1';
  let strokes = [], color = 'black', active = null, started = 0, animation = 0;
  let keyboard = false, cursor = {x:.5,y:.5};
  const countPoints = () => strokes.reduce((sum,s) => sum+s.points.length,0);
  const message = text => { $('message').textContent=text; };
  const documentValue = () => ({version:1,name:$('name').value.trim()||'Untitled',width_m:.30,height_m:.06,marker_width_m:.0015,tolerance_m:Number($('tolerance').value)/100,strokes});

  function validate(data, allowEmpty=false) {
    if (!data || data.version!==1 || !Array.isArray(data.strokes)) throw Error('Choose a version 1 Zoomer drawing JSON file.');
    if (data.strokes.length>(500) || (!allowEmpty && !data.strokes.length)) throw Error('Use between 1 and 500 strokes.');
    const tolerance=data.tolerance_m??.03;
    if (typeof tolerance!=='number' || !Number.isFinite(tolerance) || tolerance<.0005 || tolerance>.10) throw Error('Set the overall error ceiling between 0.05 and 10 cm RMS.');
    if (data.marker_width_m!==undefined && data.marker_width_m!==.0015) throw Error('The workshop uses a 1.5 mm marker.');
    if ((data.width_m!==undefined && data.width_m!==.30) || (data.height_m!==undefined && data.height_m!==.06)) throw Error('The target must use the 30 by 6 cm drawing area.');
    let count=0;
    const clean=data.strokes.map(stroke => {
      if (!stroke || !Object.hasOwn(colors,stroke.color) || !Array.isArray(stroke.points) || !stroke.points.length) throw Error('Each stroke needs points and a black, red, blue or green marker.');
      let previous=-1;
      const points=stroke.points.map(point => {
        if (!point || ['x','y','t_ms'].some(key => typeof point[key]!=='number' || !Number.isFinite(point[key]))) throw Error('Stroke coordinates and times must be finite numbers.');
        if (point.x<0 || point.x>1 || point.y<0 || point.y>1 || point.t_ms<0 || point.t_ms<previous) throw Error('Points must stay on the canvas, with times in order.');
        previous=point.t_ms;
        return {x:point.x,y:point.y,t_ms:point.t_ms};
      });
      count+=points.length;
      if (count>100000) throw Error('Use no more than 100,000 points.');
      return {color:stroke.color,points};
    });
    return {version:1,name:String(data.name??'Untitled').slice(0,100),width_m:.30,height_m:.06,marker_width_m:.0015,tolerance_m:tolerance,strokes:clean};
  }

  function render(limit=Infinity) {
    ctx.clearRect(0,0,canvas.width,canvas.height);
    ctx.lineWidth=7.5; ctx.lineCap='round'; ctx.lineJoin='round';
    let left=limit;
    for (const stroke of strokes) {
      const points=stroke.points.slice(0,Math.max(0,Math.ceil(left)));
      left-=stroke.points.length;
      if (!points.length) break;
      ctx.strokeStyle=colors[stroke.color]; ctx.fillStyle=colors[stroke.color];
      ctx.beginPath(); ctx.moveTo(points[0].x*canvas.width,points[0].y*canvas.height);
      if (points.length===1) {
        ctx.arc(points[0].x*canvas.width,points[0].y*canvas.height,3.75,0,Math.PI*2); ctx.fill();
      } else {
        for (const point of points.slice(1)) ctx.lineTo(point.x*canvas.width,point.y*canvas.height);
        ctx.stroke();
      }
    }
    if (keyboard) {
      ctx.strokeStyle='#657083'; ctx.lineWidth=2;
      const x=cursor.x*canvas.width,y=cursor.y*canvas.height;
      ctx.beginPath();ctx.moveTo(x-12,y);ctx.lineTo(x+12,y);ctx.moveTo(x,y-12);ctx.lineTo(x,y+12);ctx.stroke();
    }
    $('hint').hidden=strokes.length>0;
  }

  function update() {
    render();
    $('count').textContent=strokes.length+' stroke'+(strokes.length===1?'':'s');
    $('undo').disabled=!strokes.length;
    $('replay').disabled=!strokes.length;
    $('export').disabled=!strokes.length;
    $('strokes').replaceChildren();
    let previous=null;
    strokes.forEach((stroke,i) => {
      const li=document.createElement('li'),dot=document.createElement('i');
      dot.style.background=colors[stroke.color];
      li.append(dot,document.createTextNode((i+1)+'. '+stroke.color));
      const note=document.createElement('small'); note.textContent=previous===stroke.color?'same marker':'collect marker';
      li.append(note); $('strokes').append(li); previous=stroke.color;
    });
    try { localStorage.setItem(storageKey,JSON.stringify(documentValue())); } catch {}
  }

  function stopReplay() { cancelAnimationFrame(animation); animation=0; }
  function pointFromPointer(event) {
    const rect=canvas.getBoundingClientRect();
    return {x:Math.max(0,Math.min(1,(event.clientX-rect.left)/rect.width)),y:Math.max(0,Math.min(1,(event.clientY-rect.top)/rect.height)),t_ms:Math.max(0,Math.round(performance.now()-started))};
  }
  function start(point) {
    if (strokes.length>=500 || countPoints()>=100000) { message('The drawing has reached its stroke or point limit.'); return false; }
    stopReplay(); started=performance.now();
    active={color,points:[{x:point.x,y:point.y,t_ms:0}]}; strokes.push(active); render(); return true;
  }
  function finish() { active=null; update(); }
  for (const [name,hex] of Object.entries(colors)) {
    const button=document.createElement('button');
    button.type='button';button.className='studio-swatch';button.style.setProperty('--marker',hex);
    button.setAttribute('aria-label',name+' marker');button.setAttribute('aria-pressed',name===color);
    button.textContent=name[0].toUpperCase()+name.slice(1);
    button.onclick=() => {
      if (active && keyboard) finish();
      color=name;
      for (const other of $('palette').children) other.setAttribute('aria-pressed',other===button);
    };
    $('palette').append(button);
  }

  canvas.onpointerdown=event => {
    if (event.button!==0 || active) return;
    keyboard=false;
    if (start(pointFromPointer(event))) {canvas.setPointerCapture(event.pointerId);canvas.focus({preventScroll:true});}
  };
  canvas.onpointermove=event => {
    if (!active || keyboard || !canvas.hasPointerCapture(event.pointerId)) return;
    if (countPoints()>=100000) {finish();return;}
    active.points.push(pointFromPointer(event)); render();
  };
  function endPointer(event) {
    if (!active || keyboard) return;
    if (canvas.hasPointerCapture(event.pointerId)) canvas.releasePointerCapture(event.pointerId);
    finish();
  }
  canvas.onpointerup=endPointer;canvas.onpointercancel=endPointer;canvas.onlostpointercapture=() => {if(active&&!keyboard)finish();};
  canvas.onkeydown=event => {
    if (!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown',' ','Escape'].includes(event.key)) return;
    event.preventDefault();keyboard=true;stopReplay();
    if (event.key==='Escape') {finish();return;}
    if (event.key===' ') {active?finish():start(cursor);return;}
    const delta=event.shiftKey ? .002 : .01;
    cursor.x=Math.max(0,Math.min(1,cursor.x+(event.key==='ArrowRight'?delta:event.key==='ArrowLeft'?-delta:0)));
    cursor.y=Math.max(0,Math.min(1,cursor.y+(event.key==='ArrowDown'?delta:event.key==='ArrowUp'?-delta:0)));
    if (active && countPoints()<100000) active.points.push({...cursor,t_ms:Math.max(0,Math.round(performance.now()-started))});
    render();
  };
  canvas.onblur=() => {if(keyboard&&active)finish();keyboard=false;render();};
  $('undo').onclick=() => {stopReplay();active=null;strokes.pop();update();};
  $('clear').onclick=() => {stopReplay();active=null;strokes=[];update();message('Canvas cleared. Your draft stays in this browser.');};
  $('name').oninput=update;$('tolerance').oninput=update;

  function load(data) {
    const clean=validate(data);stopReplay();active=null;
    strokes=clean.strokes;$('name').value=clean.name;$('tolerance').value=Number((clean.tolerance_m*100).toPrecision(8));update();
  }
  $('example').onclick=async () => {
    const button=$('example');button.disabled=true;
    try {
      const response=await fetch('assets/whiteboard-example.json');
      if(!response.ok)throw Error('The recorded example could not load.');
      load(await response.json());message('Loaded the 19-stroke target used in the recorded run.');
    } catch(error) {message(error.message);} finally {button.disabled=false;}
  };
  $('import-button').onclick=() => $('import').click();
  $('import').onchange=async event => {
    try {
      const file=event.target.files[0];if(!file)return;
      if(file.size>2000000)throw Error('Choose a target JSON file smaller than 2 MB.');
      load(JSON.parse(await file.text()));message('Target imported. Stroke and point order are preserved.');
    } catch(error) {message(error instanceof SyntaxError?'That file is not valid JSON.':error.message);} finally {event.target.value='';}
  };
  $('export').onclick=() => {
    try {
      if(active)finish();const data=validate(documentValue());
      const json=JSON.stringify(data,null,2);
      $('export-json').value=json;$('export-preview').hidden=false;
      const url=URL.createObjectURL(new Blob([json],{type:'application/json'}));
      const link=document.createElement('a');link.href=url;link.download=(data.name.toLowerCase().replace(/[^a-z0-9._-]+/g,'-').replace(/^-+|-+$/g,'')||'zoomer-target')+'.json';
      document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);
      message('Target exported. Import it into the local drawing studio to train.');
    } catch(error) {message(error.message);}
  };
  $('replay').onclick=() => {
    if(active)finish();stopReplay();keyboard=false;
    const duration=strokes.reduce((sum,s)=>sum+s.points.at(-1).t_ms+150,0);
    const startTime=performance.now(),scale=Math.max(1,duration/15000);
    message('Replaying recorded stroke order, with long drawings sped up.');
    function frame(now) {
      const elapsed=(now-startTime)*scale;let offset=0,count=0;
      for(const stroke of strokes) {for(const point of stroke.points)if(offset+point.t_ms<=elapsed)count++;offset+=stroke.points.at(-1).t_ms+150;}
      render(count);
      if(elapsed<duration)animation=requestAnimationFrame(frame);
      else {render();animation=0;message('Replay complete. Export this target to use it in the local simulator.');}
    }
    animation=requestAnimationFrame(frame);
  };
  try {
    const raw=localStorage.getItem(storageKey);
    if(raw){const clean=validate(JSON.parse(raw),true);strokes=clean.strokes;$('name').value=clean.name;$('tolerance').value=clean.tolerance_m*100;}
  } catch {}
  update();
})();
