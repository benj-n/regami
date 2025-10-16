import React from 'react'
import { MapContainer, TileLayer, Marker, useMap, useMapEvents } from 'react-leaflet'
import type { LeafletMouseEvent } from 'leaflet'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'

export type LatLng = { lat: number; lng: number }

// Fix default icon paths in Vite
const DefaultIcon = L.icon({
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
  iconSize: [25, 41],
  iconAnchor: [12, 41],
  popupAnchor: [1, -34],
  shadowSize: [41, 41],
})
// @ts-ignore
L.Marker.prototype.options.icon = DefaultIcon

type PickerProps = {
  value: LatLng | null
  onChange: (next: LatLng) => void
  height?: number | string
}

// Center on Trois-Rivières, Quebec (free OSM tiles)
const DEFAULT_CENTER: [number, number] = [46.343, -72.543]
const DEFAULT_ZOOM = 7

function ClickHandler({ onPick }: { onPick: (lat: number, lng: number) => void }) {
  useMapEvents({
    click(e: LeafletMouseEvent) {
      onPick(e.latlng.lat, e.latlng.lng)
    },
  })
  return null
}

const RecenterOnValue: React.FC<{ value: LatLng | null }> = ({ value }) => {
  const map = useMap()
  React.useEffect(() => {
    if (value) {
      map.setView([value.lat, value.lng], 10)
    }
  }, [value?.lat, value?.lng])
  return null
}

const MapPicker: React.FC<PickerProps> = ({ value, onChange, height = 320 }) => {
  const center = value ? ([value.lat, value.lng] as [number, number]) : DEFAULT_CENTER
  const zoom = value ? 10 : DEFAULT_ZOOM
  return (
    <div data-testid="map-picker" style={{ height, width: '100%', borderRadius: 6, overflow: 'hidden' }}>
      <MapContainer center={center as unknown as [number, number]} zoom={zoom} style={{ height: '100%', width: '100%' }}>
        <TileLayer
          attribution={'© OpenStreetMap contributors'}
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <RecenterOnValue value={value} />
        <ClickHandler onPick={(lat, lng) => onChange({ lat, lng })} />
        {value && <Marker position={[value.lat, value.lng]} />}
      </MapContainer>
    </div>
  )
}

export default MapPicker
