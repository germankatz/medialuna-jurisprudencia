<script setup>
import { computed } from 'vue'

const props = defineProps({
  modelValue: {
    type: [Number, String, null],
    default: null
  },
  origins: {
    type: Array,
    required: true
  },
  showAuto: {
    type: Boolean,
    default: false
  },
  showAll: {
    type: Boolean,
    default: false
  },
  size: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  textSize: {
    type: String,
    default: 'md',
    validator: (v) => ['sm', 'md', 'lg'].includes(v)
  },
  disabled: {
    type: Boolean,
    default: false
  },
  placeholder: {
    type: String,
    default: 'Seleccionar origen'
  }
})

const emit = defineEmits(['update:modelValue'])

// Obtener el origen seleccionado actualmente
const selectedOrigen = computed(() => {
  if (props.modelValue === 'auto') return null
  return props.origins.find(o => o.id === props.modelValue)
})

// Color de fondo basado en el origen seleccionado
const selectedColor = computed(() => {
  if (props.modelValue === 'auto') return '#3B82F6' // azul para auto
  if (props.modelValue === null && props.showAll) return '#6B7280' // gris para "Todos"
  return selectedOrigen.value?.color || '#6B7280' // gris por defecto
})

// Clases de tamaño (altura y padding)
const sizeClasses = computed(() => {
  if (props.size === 'sm') return 'h-7 pl-7 pr-7'
  if (props.size === 'lg') return 'h-12 pl-9 pr-10'
  return 'h-9 pl-7 pr-8'
})

// Clases de tamaño de texto
const textSizeClasses = computed(() => {
  if (props.textSize === 'sm') return 'text-xs'
  if (props.textSize === 'lg') return 'text-base'
  return 'text-sm'
})

// Clases del indicador de color
const indicatorClasses = computed(() => {
  if (props.size === 'lg') return 'left-3 w-3 h-3'
  return 'left-2 w-2.5 h-2.5'
})

// Clases del icono de flecha
const arrowClasses = computed(() => {
  if (props.size === 'lg') return 'right-3 w-5 h-5'
  return 'right-2 w-4 h-4'
})

const handleChange = (event) => {
  const value = event.target.value
  if (value === 'auto') {
    emit('update:modelValue', 'auto')
  } else if (value === '') {
    emit('update:modelValue', null)
  } else {
    emit('update:modelValue', parseInt(value, 10))
  }
}
</script>

<template>
  <div class="relative inline-block">
    <!-- Indicador de color -->
    <span
      class="absolute top-1/2 -translate-y-1/2 rounded-full"
      :class="indicatorClasses"
      :style="{ backgroundColor: selectedColor }"
    />

    <select
      :value="modelValue ?? ''"
      @change="handleChange"
      :disabled="disabled"
      class="appearance-none bg-white border border-zinc-300 rounded-md font-medium
             focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500
             disabled:bg-zinc-100 disabled:cursor-not-allowed cursor-pointer
             transition-colors duration-150"
      :class="[sizeClasses, textSizeClasses]"
    >
      <!-- Opción Todos (solo si showAll=true) -->
      <option v-if="showAll" value="">
        {{ placeholder }}
      </option>

      <!-- Opción Auto (solo si showAuto=true) -->
      <option v-if="showAuto" value="auto">
        Auto (IA)
      </option>

      <!-- Placeholder (cuando no hay showAll ni showAuto) -->
      <option v-if="!showAuto && !showAll" value="" disabled>
        {{ placeholder }}
      </option>

      <!-- Opciones de origen -->
      <option
        v-for="origen in origins"
        :key="origen.id"
        :value="origen.id"
      >
        {{ origen.abreviacion }}
      </option>
    </select>

    <!-- Icono de flecha -->
    <svg
      class="absolute top-1/2 -translate-y-1/2 text-zinc-400 pointer-events-none"
      :class="arrowClasses"
      fill="none"
      stroke="currentColor"
      viewBox="0 0 24 24"
    >
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
    </svg>
  </div>
</template>
