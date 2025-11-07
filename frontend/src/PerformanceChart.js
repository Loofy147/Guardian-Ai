import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const PerformanceChart = ({ data }) => {
  const ref = useRef();

  useEffect(() => {
    if (data) {
      const svg = d3.select(ref.current);
      const width = 500;
      const height = 300;
      const margin = { top: 20, right: 30, bottom: 40, left: 40 };

      const chartData = [
        { name: 'Algorithm', value: data.total_cost_algorithm },
        { name: 'Optimal', value: data.total_cost_optimal },
      ];

      const x = d3.scaleBand()
        .domain(chartData.map(d => d.name))
        .range([margin.left, width - margin.right])
        .padding(0.1);

      const y = d3.scaleLinear()
        .domain([0, d3.max(chartData, d => d.value)])
        .nice()
        .range([height - margin.bottom, margin.top]);

      svg.selectAll('*').remove(); // Clear previous chart

      svg.append('g')
        .attr('fill', 'steelblue')
        .selectAll('rect')
        .data(chartData)
        .join('rect')
          .attr('x', d => x(d.name))
          .attr('y', d => y(d.value))
          .attr('height', d => y(0) - y(d.value))
          .attr('width', x.bandwidth());

      svg.append('g')
        .attr('transform', `translate(0,${height - margin.bottom})`)
        .call(d3.axisBottom(x));

      svg.append('g')
        .attr('transform', `translate(${margin.left},0)`)
        .call(d3.axisLeft(y));
    }
  }, [data]);

  return (
    <svg ref={ref} width={500} height={300}></svg>
  );
};

export default PerformanceChart;
