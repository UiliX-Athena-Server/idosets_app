import { onSettled } from 'solid-js'
import {
  CategoryScale,
  Chart,
  Filler,
  LinearScale,
  LineController,
  LineElement,
  PointElement,
  Tooltip,
} from 'chart.js'

Chart.register(LineController, LineElement, PointElement, LinearScale, CategoryScale, Tooltip, Filler)

/**
 * props: title, values (number[]), labels (string[]), color, format(value) -> string,
 *        whole (only whole-number ticks)
 */
export default function LineChart(props) {
  let canvas

  onSettled(() => {
    const styles = getComputedStyle(document.documentElement)
    const text = styles.getPropertyValue('--text-muted').trim() || '#999'
    const grid = styles.getPropertyValue('--border').trim() || 'rgba(128,128,128,0.2)'
    const format = props.format || ((v) => String(v))

    const chart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: props.labels,
        datasets: [
          {
            label: props.title,
            data: props.values,
            borderColor: props.color,
            backgroundColor: `${props.color}33`,
            pointBackgroundColor: props.color,
            fill: true,
            tension: 0.25,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              title: (items) => items[0]?.label ?? '',
              label: (item) => format(item.parsed.y),
            },
          },
        },
        scales: {
          x: { ticks: { color: text, maxTicksLimit: 6 }, grid: { color: grid } },
          y: {
            beginAtZero: false,
            ticks: { color: text, precision: props.whole ? 0 : undefined, callback: (v) => format(v) },
            grid: { color: grid },
          },
        },
      },
    })

    return () => chart.destroy()
  })

  return (
    <figure class="chart">
      <figcaption class="field-label">{props.title}</figcaption>
      <div class="chart-canvas">
        <canvas ref={canvas} aria-label={props.title} role="img" />
      </div>
    </figure>
  )
}
