import React from 'react'
import ReactDatePicker, { registerLocale } from 'react-datepicker'
import { fr } from 'date-fns/locale/fr'
import 'react-datepicker/dist/react-datepicker.css'

// Register French locale
registerLocale('fr', fr)

interface DateTimePickerProps {
  selected: Date | null
  onChange: (date: Date | null) => void
  label?: string
  placeholderText?: string
  disabled?: boolean
  minDate?: Date
  maxDate?: Date
  showTimeSelect?: boolean
  dateFormat?: string
  id?: string
}

const DateTimePicker: React.FC<DateTimePickerProps> = ({
  selected,
  onChange,
  label,
  placeholderText = 'Sélectionner une date...',
  disabled = false,
  minDate,
  maxDate,
  showTimeSelect = true,
  dateFormat = 'dd/MM/yyyy HH:mm',
  id,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
      {label && (
        <label htmlFor={id} style={{ fontWeight: 500, fontSize: '0.9em' }}>
          {label}
        </label>
      )}
      <ReactDatePicker
        id={id}
        selected={selected}
        onChange={onChange}
        showTimeSelect={showTimeSelect}
        timeFormat="HH:mm"
        timeIntervals={15}
        dateFormat={dateFormat}
        placeholderText={placeholderText}
        disabled={disabled}
        minDate={minDate}
        maxDate={maxDate}
        locale="fr"
        todayButton="Aujourd'hui"
        timeCaption="Heure"
        className="date-picker-input"
        calendarClassName="date-picker-calendar"
        wrapperClassName="date-picker-wrapper"
      />
    </div>
  )
}

export default DateTimePicker
