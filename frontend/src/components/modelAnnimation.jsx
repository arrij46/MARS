import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

export default function GraphNNAnimation({ width = 900, height = 600 }) {
  const svgRef = useRef();
  let edges = [];

  useEffect(() => {
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const margin = 80;
    const centerX = width / 2;
    const centerY = height / 2;

    const totalPoints = 60;
    const pointsPerCluster = totalPoints / 3;
    // const clusterColors = ['#66a7d5ff', '#f491a5ff', '#c578c5ff']; // Dusty Blue, Baby Pink, Lilac
const clusterColors = ['rgb(0, 168, 151)', 'rgba(107, 147, 240, 1)', 'rgba(74, 85, 100, 1)'];
  const points = d3.range(totalPoints).map((i) => ({
      x: Math.random() * (width - 2 * margin) + margin,
      y: Math.random() * (height - 2 * margin) + margin,
      cluster: Math.floor(i / pointsPerCluster),
    }));

    const phases = [scatterPhase, clusterPhase, nnPhase];
    let currentPhase = 0;

    function nextPhase() {
      if (currentPhase < phases.length) {
        phases[currentPhase++]();
      }
    }

    //  Scatter Phase
    function scatterPhase() {
      svg.selectAll('circle')
        .data(points)
        .enter()
        .append('circle')
        .attr('cx', d => d.x)
        .attr('cy', d => d.y)
        .attr('r', 8)
        .attr('fill', '#aaa');
      setTimeout(nextPhase, 1500);
    }

function clusterPhase() {
  svg.selectAll('line').remove(); // clear old links

  // Colorize points
  svg.selectAll('circle')
    .transition()
    .duration(1000)
    .attr('fill', d => clusterColors[d.cluster]);

  const grouped = d3.groups(points, d => d.cluster);

  grouped.forEach(([clusterIndex, clusterPoints]) => {
    const edges = [];

    // Build MST-like sparse connectivity
    const unvisited = new Set(clusterPoints);
    const visited = new Set();

    // Start from a random point
    const start = clusterPoints[Math.floor(Math.random() * clusterPoints.length)];
    visited.add(start);
    unvisited.delete(start);

    while (unvisited.size > 0) {
      let closestA = null;
      let closestB = null;
      let minDist = Infinity;

      visited.forEach(a => {
        unvisited.forEach(b => {
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy);
          if (dist < minDist) {
            minDist = dist;
            closestA = a;
            closestB = b;
          }
        });
      });

      edges.push([closestA, closestB]);
      visited.add(closestB);
      unvisited.delete(closestB);
    }

    // Optionally add a few random extra short edges for visual richness
    for (let i = 0; i < clusterPoints.length / 3; i++) {
      const a = clusterPoints[Math.floor(Math.random() * clusterPoints.length)];
      const b = clusterPoints[Math.floor(Math.random() * clusterPoints.length)];
      if (a !== b) {
        const dx = a.x - b.x;
        const dy = a.y - b.y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 150) edges.push([a, b]);
      }
    }

    // Draw the lines
    svg.selectAll(`.cluster-line-${clusterIndex}`)
      .data(edges)
      .enter()
      .append('line')
      .attr('class', `cluster-line-${clusterIndex}`)
      .attr('x1', d => d[0].x)
      .attr('y1', d => d[0].y)
      .attr('x2', d => d[1].x)
      .attr('y2', d => d[1].y)
      .attr('stroke', clusterColors[clusterIndex])
      .attr('stroke-width', 1.2)
      .attr('opacity', 0)
      .transition()
      .duration(700)
      .delay((d, i) => i * 10)
      .attr('opacity', 0.8);
  });

  setTimeout(nnPhase, 2500);
}

    // 🧠 Neural Network Phase
function nnPhase() {
  svg.selectAll('*').remove();

  const nnGroup = svg.append('g')
    .attr('transform', `translate(${centerX - 320}, ${centerY - 230}) scale(1.5)`);

  const layers = [
    [{ x: 0, y: 100 }, { x: 0, y: 200 }],
    [{ x: 150, y: 80 }, { x: 150, y: 150 }, { x: 150, y: 220 }], // middle neuron = index 1
    [{ x: 300, y: 120 }, { x: 300, y: 200 }, { x: 300, y: 280 }],
  ];

  // Draw neurons
  layers.forEach((layer, li) => {
    nnGroup.selectAll(`.layer${li}`)
      .data(layer)
      .enter()
      .append('circle')
      .attr('cx', d => d.x)
      .attr('cy', d => d.y)
      .attr('r', 8)
      .attr('fill', 'white')
      .attr('stroke', '#555');
  });

  // Draw connections
  for (let i = 0; i < layers.length - 1; i++) {
    layers[i].forEach(a => {
      layers[i + 1].forEach(b => {
        nnGroup.append('line')
          .attr('x1', a.x)
          .attr('y1', a.y)
          .attr('x2', b.x)
          .attr('y2', b.y)
          .attr('stroke', '#bbb')
          .attr('stroke-width', 1);
      });
    });
  }

  const boxes = [
    { label: 'Neutral', color: clusterColors[0], x: 400, y: 80 },
    { label: 'Conflict', color: clusterColors[1], x: 400, y: 160 },
    { label: 'Duplicate', color: clusterColors[2], x: 400, y: 240 },
  ];

  const boxGroup = nnGroup.selectAll('.boxes')
    .data(boxes)
    .enter()
    .append('g')
    .attr('class', 'box-group');

  boxGroup.append('rect')
    .attr('x', d => d.x)
    .attr('y', d => d.y)
    .attr('width', 100)
    .attr('height', 40)
    .attr('fill', d => d.color)
    .attr('opacity', 1)
    .attr('rx', 6);

  boxGroup.append('text')
    .attr('x', d => d.x + 50)
    .attr('y', d => d.y + 25)
    .attr('fill', 'white')
    .attr('text-anchor', 'middle')
    .attr('font-size', 14)
    .text(d => d.label);

  const sequences = [
    { color: clusterColors[0], targetIndex: 0 },
    { color: clusterColors[1], targetIndex: 1 },
    { color: clusterColors[2], targetIndex: 2 },
  ];

  let current = 0;

  function animatePair() {
    if (current >= sequences.length) {
      current = 0;
      setTimeout(animatePair, 1500);
      return;
    }

    const seq = sequences[current];
    const targetBox = boxes[seq.targetIndex];
    const targetY = layers[2][seq.targetIndex].y;

    // Randomly choose which middle neuron each point passes through (0, 1, or 2)
    const midIndexA = Math.floor(Math.random() * 3);
    const midIndexB = Math.floor(Math.random() * 3);

    // Define two slightly different paths for A and B
    const paths = [
      [
        { x: -50, y: 100 },
        layers[0][0],
        layers[1][midIndexA],
        layers[2][seq.targetIndex],
        { x: 450, y: targetBox.y + 20 }
      ],
      [
        { x: -50, y: 200 },
        layers[0][1],
        layers[1][midIndexB],
        layers[2][seq.targetIndex],
        { x: 450, y: targetBox.y + 20 }
      ]
    ];

    // Animate each circle through its path
    paths.forEach((path, i) => {
      const circle = nnGroup.append('circle')
        .attr('r', 8)
        .attr('fill', seq.color)
        .attr('cx', path[0].x)
        .attr('cy', path[0].y);

      let t = circle;
      for (let j = 1; j < path.length; j++) {
        t = t.transition()
          .duration(1000)
          .attr('cx', path[j].x)
          .attr('cy', path[j].y);
      }

      t.on('end', function () {
        d3.select(this)
          .transition()
          .duration(500)
          .style('opacity', 0)
          .remove();
      });
    });

    current++;
    setTimeout(animatePair, 2000);
  }

  animatePair();
}

    nextPhase();
  }, [width, height]);

//   return (
//     <div style={{
//       display: 'flex',
//       justifyContent: 'center',
//       alignItems: 'center',
//       height: '100vh',
//       width: '100vw',
//       overflow: 'hidden',
//     }}>
//       <h2 className='heading'>Conflict and Duplicate Detection <br/>Model Animation<br/></h2>
//       {/* <h4>Please Wait</h4> */}
//       <svg ref={svgRef} width={width} height={height} className='animation' />
//       <style>{`
//         @keyframes glowPulse {
//           0% { filter: drop-shadow(0 0 0 rgba(0,0,0,0)); }
//           50% { filter: drop-shadow(0 0 15px var(--glow-color)); }
//           100% { filter: drop-shadow(0 0 0 rgba(0,0,0,0)); }
//         }
//         .glow {
//           animation: glowPulse 1.5s ease-in-out;
//         }
//       `}</style>
  
//     </div>
//   );
// }
  return (
    <div
      style={{
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        height: '100vh',
        width: '100vw',
        overflow: 'hidden',
        fontSize:'45px',
        fontWeight:'bold',
        position: 'relative',
        flexDirection: 'column',
      }}
    >
      <h2 className="heading text-center mb-2 styling-header"       style={{

        fontSize:'45px',
        fontWeight:'bold',
      
      }}>
        Conflict and Duplicate Detection <br /> Model Animation
      </h2>

      {/* 🟢 Please Wait Message */}
      <p
        id="wait-message"
        style={{
          fontSize: "20px",
          color: "#555",
          marginBottom: "10px",
          animation: "fadeInOut 2s ease-in-out infinite",
        }}
      >
        Please wait while we check your requirements for any conflicts and duplicates...
      </p>

      <svg ref={svgRef} width={width} height={height} className="animation" />

      <style>{`
        @keyframes glowPulse {
          0% { filter: drop-shadow(0 0 0 rgba(0,0,0,0)); }
          50% { filter: drop-shadow(0 0 15px var(--glow-color)); }
          100% { filter: drop-shadow(0 0 0 rgba(0,0,0,0)); }
        }
        .glow {
          animation: glowPulse 1.5s ease-in-out;
        }
        @keyframes fadeInOut {
          0%, 100% { opacity: 0.5; }
          50% { opacity: 1; }
        }
      `}</style>
    </div>
  );
}