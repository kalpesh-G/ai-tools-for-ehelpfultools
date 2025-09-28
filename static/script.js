const promptBox = document.getElementById("prompt");
const manualJSON = document.getElementById("manualJSON");
const loadExampleBtn = document.getElementById("loadExample");
const generateBtn = document.getElementById("generateAI");
const transitionTableDiv = document.getElementById("transitionTable");
const stateDiagramSVG = document.getElementById("stateDiagram");
const testInputBox = document.getElementById("testInput");
const traceBtn = document.getElementById("traceInput");
const traceLogDiv = document.getElementById("traceLog");
const themeToggleBtn = document.getElementById("themeToggle");

let currentMachine = null;

// Example machine (detect 101)
const EXAMPLE_MACHINE = {
  "alphabet": ["0","1"],
  "states": [
    {"id":"S0","output":"0","start":true},
    {"id":"S1","output":"0"},
    {"id":"S2","output":"1"}
  ],
  "transitions": [
    {"from":"S0","input":"1","to":"S1"},
    {"from":"S1","input":"0","to":"S2"},
    {"from":"S2","input":"1","to":"S1"}
  ]
};

// Dark/Light Mode
themeToggleBtn.addEventListener("click", () => {
  document.body.classList.toggle("dark-mode");
});

// Load example machine
loadExampleBtn.addEventListener("click", () => {
  currentMachine = EXAMPLE_MACHINE;
  manualJSON.value = JSON.stringify(currentMachine, null, 2);
  renderTransitionTable(currentMachine);
  renderStateDiagram(currentMachine);
});

// Generate AI Machine using Gemini API
generateBtn.addEventListener("click", async () => {
  const promptText = promptBox.value.trim();
  if(!promptText) return alert("Enter a prompt!");

  transitionTableDiv.innerHTML = "Generating machine...";
  try {
    const response = await fetch("/api/generate", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({prompt: promptText})
    });
    const data = await response.json();
    currentMachine = data.response; // assuming server returns {"response":{...machine JSON...}}
    manualJSON.value = JSON.stringify(currentMachine, null, 2);
    renderTransitionTable(currentMachine);
    renderStateDiagram(currentMachine);
  } catch (err) {
    console.error(err);
    transitionTableDiv.innerHTML = "Error generating machine.";
  }
});

// Load manual JSON
manualJSON.addEventListener("change", () => {
  try {
    const json = JSON.parse(manualJSON.value);
    currentMachine = json;
    renderTransitionTable(json);
    renderStateDiagram(json);
  } catch (err) {
    alert("Invalid JSON");
  }
});

// Render transition table
function renderTransitionTable(machine){
  if(!machine) return;
  let html = `<table border="1" cellspacing="0" cellpadding="6"><tr><th>State</th><th>Output</th>`;
  machine.alphabet.forEach(sym => html += `<th>${sym}</th>`);
  html += `</tr>`;
  machine.states.forEach(state=>{
    html += `<tr><td>${state.id}</td><td>${state.output}</td>`;
    machine.alphabet.forEach(sym=>{
      const t = machine.transitions.find(tr=>tr.from===state.id && tr.input===sym);
      html += `<td>${t ? t.to : "-"}</td>`;
    });
    html += `</tr>`;
  });
  html += `</table>`;
  transitionTableDiv.innerHTML = html;
}

// Render state diagram (simple circle layout)
function renderStateDiagram(machine){
  if(!machine) return;
  const svg = d3.select("#stateDiagram");
  svg.selectAll("*").remove();
  const width = +svg.attr("width");
  const height = +svg.attr("height");
  const radius = Math.min(width, height)/2 - 50;
  const states = machine.states;
  const angleStep = (2*Math.PI)/states.length;

  // Positions
  states.forEach((s,i)=>{
    s.x = width/2 + radius * Math.cos(i*angleStep);
    s.y = height/2 + radius * Math.sin(i*angleStep);
  });

  // Draw transitions
  const transitions = machine.transitions;
  transitions.forEach(tr=>{
    const from = states.find(s=>s.id===tr.from);
    const to = states.find(s=>s.id===tr.to);
    svg.append("line")
      .attr("x1",from.x).attr("y1",from.y)
      .attr("x2",to.x).attr("y2",to.y)
      .attr("stroke","#2196F3").attr("marker-end","url(#arrow)");
  });

  // Arrow marker
  svg.append("defs").append("marker")
    .attr("id","arrow").attr("markerWidth","10").attr("markerHeight","10")
    .attr("refX","6").attr("refY","3")
    .attr("orient","auto").append("path")
    .attr("d","M0,0 L0,6 L9,3 z").attr("fill","#2196F3");

  // Draw states
  states.forEach(s=>{
    svg.append("circle")
      .attr("cx",s.x).attr("cy",s.y).attr("r",25)
      .attr("fill","#4CAF50").attr("stroke","#2196F3").attr("stroke-width",2);
    svg.append("text")
      .attr("x",s.x).attr("y",s.y+5).attr("text-anchor","middle")
      .attr("fill","#fff").text(s.id);
  });
}

// Trace input
traceBtn.addEventListener("click", ()=>{
  if(!currentMachine) return;
  const input = testInputBox.value.trim().split("");
  let state = currentMachine.states.find(s=>s.start);
  if(!state) return alert("No start state defined!");
  traceLogDiv.innerHTML = `Start at ${state.id}, Output: ${state.output}<br>`;
  input.forEach(sym=>{
    const tr = currentMachine.transitions.find(t=>t.from===state.id && t.input===sym);
    if(!tr){
      traceLogDiv.innerHTML += `No transition from ${state.id} on ${sym}<br>`;
      return;
    }
    state = currentMachine.states.find(s=>s.id===tr.to);
    traceLogDiv.innerHTML += `Input: ${sym} -> State: ${state.id}, Output: ${state.output}<br>`;
  });
});
