"use client";

import { ColorType, createChart, IChartApi, ISeriesApi, UTCTimestamp } from "lightweight-charts";
import { useEffect, useRef } from "react";

// 2024-01-01 00:00:00 UTC — base for index-based candle timestamps
const BASE_TS = 1704067200 as UTCTimestamp;
const SECONDS_PER_BAR = 86400; // 1 day per index unit

type Candle = { t: number; o: number; h: number; l: number; c: number; v: number };
type OverlayPoint = { x: number; fast: number; slow: number };

interface TradingChartProps {
  candles: Candle[];
  overlayPoints: OverlayPoint[];
}

export function TradingChart({ candles, overlayPoints }: TradingChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const closeSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const fastSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);
  const slowSeriesRef = useRef<ISeriesApi<"Line"> | null>(null);

  // Mount chart once
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      width: containerRef.current.clientWidth,
      height: 240,
      layout: {
        background: { type: ColorType.Solid, color: "#060a12" },
        textColor: "#d7e3ff",
      },
      grid: {
        vertLines: { color: "#1d2a44" },
        horzLines: { color: "#1d2a44" },
      },
      crosshair: { mode: 1 },
      rightPriceScale: { borderColor: "#1d2a44" },
      timeScale: { borderColor: "#1d2a44", timeVisible: false },
    });

    chartRef.current = chart;
    closeSeriesRef.current = chart.addLineSeries({ color: "#8fb6ff", lineWidth: 2, title: "Close" });
    fastSeriesRef.current = chart.addLineSeries({ color: "#5ef2a4", lineWidth: 1, title: "Fast EMA" });
    slowSeriesRef.current = chart.addLineSeries({ color: "#ffba5e", lineWidth: 1, title: "Slow EMA" });

    const handleResize = () => {
      if (containerRef.current) {
        chart.applyOptions({ width: containerRef.current.clientWidth });
      }
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chart.remove();
    };
  }, []);

  // Update close price series when candles change
  useEffect(() => {
    if (!closeSeriesRef.current || candles.length === 0) return;
    closeSeriesRef.current.setData(
      candles.map((c) => ({
        time: (BASE_TS + c.t * SECONDS_PER_BAR) as UTCTimestamp,
        value: c.c,
      }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [candles]);

  // Update overlay series when overlayPoints change, aligned to candle times
  useEffect(() => {
    if (!fastSeriesRef.current || !slowSeriesRef.current || overlayPoints.length === 0 || candles.length === 0) return;

    // EMA warmup offset: overlay starts after the first (candles.length - overlayPoints.length) candles
    const offset = Math.max(0, candles.length - overlayPoints.length);

    fastSeriesRef.current.setData(
      overlayPoints.map((p) => ({
        time: (BASE_TS + (offset + p.x) * SECONDS_PER_BAR) as UTCTimestamp,
        value: p.fast,
      }))
    );
    slowSeriesRef.current.setData(
      overlayPoints.map((p) => ({
        time: (BASE_TS + (offset + p.x) * SECONDS_PER_BAR) as UTCTimestamp,
        value: p.slow,
      }))
    );
    chartRef.current?.timeScale().fitContent();
  }, [overlayPoints, candles]);

  return <div ref={containerRef} className="h-60 w-full rounded" />;
}
