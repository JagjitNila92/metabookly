'use client'

import { ComposableMap, Geographies, Geography, ZoomableGroup } from 'react-simple-maps'
import { Tooltip } from 'react-tooltip'

// Natural Earth world topology
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json'

// ISO-2 → ISO-3 lookup (common countries)
const ISO2_TO_ISO3: Record<string, string> = {
  GB:'GBR', US:'USA', DE:'DEU', FR:'FRA', ES:'ESP', IT:'ITA', NL:'NLD',
  BE:'BEL', AU:'AUS', CA:'CAN', JP:'JPN', CN:'CHN', IN:'IND', BR:'BRA',
  ZA:'ZAF', MX:'MEX', AR:'ARG', NG:'NGA', EG:'EGY', KE:'KEN', GH:'GHA',
  PL:'POL', SE:'SWE', NO:'NOR', DK:'DNK', FI:'FIN', CH:'CHE', AT:'AUT',
  PT:'PRT', IE:'IRL', NZ:'NZL', SG:'SGP', HK:'HKG', AE:'ARE', SA:'SAU',
  RU:'RUS', TR:'TUR', ZW:'ZWE', TZ:'TZA', UG:'UGA', RW:'RWA', ET:'ETH',
  PK:'PAK', BD:'BGD', LK:'LKA', ID:'IDN', MY:'MYS', PH:'PHL', TH:'THA',
  VN:'VNM', KR:'KOR', IL:'ISR', MA:'MAR', DZ:'DZA', TN:'TUN',
}

type CountryData = {
  country_code: string
  order_count: number
  retailer_count: number
}

type Props = {
  data: CountryData[]
}

export default function WorldMap({ data }: Props) {
  // Build lookup: ISO-3 → counts
  const byIso3 = Object.fromEntries(
    data.map(d => [ISO2_TO_ISO3[d.country_code] ?? d.country_code, d])
  )

  const maxOrders = Math.max(...data.map(d => d.order_count), 1)

  function getColor(iso3: string): string {
    const d = byIso3[iso3]
    if (!d) return '#e2e8f0'  // slate-200 — no data
    const intensity = d.order_count / maxOrders
    if (intensity > 0.75) return '#92400e'  // amber-800
    if (intensity > 0.5)  return '#b45309'  // amber-700
    if (intensity > 0.25) return '#d97706'  // amber-600
    return '#fbbf24'                          // amber-400 — light activity
  }

  return (
    <div className="w-full" style={{ height: 340 }}>
      <ComposableMap
        projectionConfig={{ scale: 140 }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup>
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const iso3 = geo.properties.ISO_A3 ?? geo.id
                const d = byIso3[iso3]
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={getColor(iso3)}
                    stroke="#fff"
                    strokeWidth={0.4}
                    data-tooltip-id="map-tip"
                    data-tooltip-content={
                      d
                        ? `${geo.properties.NAME}: ${d.order_count} order${d.order_count !== 1 ? 's' : ''} · ${d.retailer_count} retailer${d.retailer_count !== 1 ? 's' : ''}`
                        : geo.properties.NAME
                    }
                    style={{
                      default: { outline: 'none' },
                      hover:   { fill: '#f59e0b', outline: 'none', cursor: d ? 'pointer' : 'default' },
                      pressed: { outline: 'none' },
                    }}
                  />
                )
              })
            }
          </Geographies>
        </ZoomableGroup>
      </ComposableMap>
      <Tooltip id="map-tip" style={{ fontSize: 12 }} />

      {/* Legend */}
      <div className="flex items-center gap-2 mt-2 justify-end pr-2">
        <span className="text-xs text-slate-400">Orders:</span>
        {[
          { color: '#fbbf24', label: 'Low' },
          { color: '#d97706', label: '' },
          { color: '#b45309', label: '' },
          { color: '#92400e', label: 'High' },
        ].map(({ color, label }) => (
          <div key={color} className="flex items-center gap-1">
            <span className="inline-block w-3 h-3 rounded-sm" style={{ background: color }} />
            {label && <span className="text-xs text-slate-400">{label}</span>}
          </div>
        ))}
        <div className="flex items-center gap-1">
          <span className="inline-block w-3 h-3 rounded-sm bg-slate-200" />
          <span className="text-xs text-slate-400">None</span>
        </div>
      </div>
    </div>
  )
}
