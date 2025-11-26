import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

const PerformanceChart = ({ data }) => {
    const d3Container = useRef(null);

    useEffect(() => {
        if (data && d3Container.current) {
            const svg = d3.select(d3Container.current);
            svg.selectAll("*").remove(); // Clear SVG before redrawing

            const width = 500;
            const height = 300;
            const margin = { top: 20, right: 30, bottom: 30, left: 40 };

            const x = d3.scaleTime()
                .domain(d3.extent(data, d => new Date(d.timestamp)))
                .range([margin.left, width - margin.right]);

            const y = d3.scaleLinear()
                .domain([0, d3.max(data, d => Math.max(d.cost, d.optimal_cost))])
                .range([height - margin.bottom, margin.top]);

            svg.append("g")
                .attr("transform", `translate(0,${height - margin.bottom})`)
                .call(d3.axisBottom(x));

            svg.append("g")
                .attr("transform", `translate(${margin.left},0)`)
                .call(d3.axisLeft(y));

            const line = d3.line()
                .x(d => x(new Date(d.timestamp)))
                .y(d => y(d.cost));

            const optimalLine = d3.line()
                .x(d => x(new Date(d.timestamp)))
                .y(d => y(d.optimal_cost));

            svg.append("path")
                .datum(data)
                .attr("fill", "none")
                .attr("stroke", "steelblue")
                .attr("stroke-width", 1.5)
                .attr("d", line);

            svg.append("path")
                .datum(data)
                .attr("fill", "none")
                .attr("stroke", "red")
                .attr("stroke-width", 1.5)
                .attr("d", optimalLine);
        }
    }, [data]);

    return (
        <svg
            className="d3-component"
            width={500}
            height={300}
            ref={d3Container}
        />
    );
};

export default PerformanceChart;
