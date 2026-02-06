<script setup>
import { computed } from 'vue'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  FileText,
  Trash2,
  Loader2,
  CheckCircle2,
  XCircle,
  RefreshCw,
  Play,
  X,
  Sparkles
} from 'lucide-vue-next'
import OriginSelect from './OriginSelect.vue'

const props = defineProps({
  files: {
    type: Array,
    required: true
  },
  origins: {
    type: Array,
    default: () => []
  },
  isProcessing: {
    type: Boolean,
    default: false
  },
  canProcess: {
    type: Boolean,
    default: false
  },
  autoClassifyEnabled: {
    type: Boolean,
    default: false
  },
  isClassifying: {
    type: Boolean,
    default: false
  },
  classifyingProgress: {
    type: Object,
    default: () => ({ current: 0, total: 0 })
  }
})

const emit = defineEmits(['remove', 'retry', 'process', 'clear', 'update-origen', 'classify-all'])

// Computed para estadísticas
const stats = computed(() => {
  const pending = props.files.filter(f => f.status === 'pending').length
  const uploading = props.files.filter(f => f.status === 'uploading').length
  const success = props.files.filter(f => f.status === 'success').length
  const error = props.files.filter(f => f.status === 'error').length
  return { pending, uploading, success, error, total: props.files.length }
})

// Computed para verificar si hay archivos pendientes con origen 'auto'
const hasAutoOriginFiles = computed(() => {
  return props.files.some(f => f.status === 'pending' && f.origen === 'auto')
})

// Computed para el porcentaje de progreso de catalogación
const classifyProgressPercent = computed(() => {
  if (!props.classifyingProgress || props.classifyingProgress.total === 0) return 0
  return Math.round((props.classifyingProgress.current / props.classifyingProgress.total) * 100)
})

// Formatear tamaño de archivo
const formatSize = (bytes) => {
  if (bytes === 0) return '0 Bytes'
  const k = 1024
  const sizes = ['Bytes', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i]
}

// Obtener clases de estado para el borde
const getStatusClasses = (status) => {
  switch (status) {
    case 'uploading':
      return 'border-l-4 border-l-blue-500 bg-blue-50/50'
    case 'success':
      return 'border-l-4 border-l-green-500 bg-green-50/50'
    case 'error':
      return 'border-l-4 border-l-red-500 bg-red-50/50'
    default:
      return 'border-l-4 border-l-zinc-300'
  }
}

// Obtener origen por ID
const getOrigenById = (id) => {
  if (id === 'auto') return { abreviacion: 'Auto', color: '#3B82F6' }
  return props.origins.find(o => o.id === id) || null
}

// Handler para cambio de origen
const handleOrigenChange = (fileId, newOrigen) => {
  emit('update-origen', fileId, newOrigen)
}
</script>

<template>
  <div class="space-y-4">
    <!-- Header con estadísticas -->
    <div class="flex items-center justify-between">
      <div>
        <h3 class="text-lg font-semibold text-zinc-800">
          Cola de subida
        </h3>
        <p class="text-sm text-zinc-500">
          {{ stats.total }} archivo{{ stats.total !== 1 ? 's' : '' }} seleccionado{{ stats.total !== 1 ? 's' : '' }}
          <template v-if="stats.success > 0">
            <span class="text-green-600 ml-2">{{ stats.success }} completado{{ stats.success !== 1 ? 's' : '' }}</span>
          </template>
          <template v-if="stats.error > 0">
            <span class="text-red-600 ml-2">{{ stats.error }} con error</span>
          </template>
        </p>
      </div>

      <!-- Botón Catalogar todo con barra de progreso -->
      <div v-if="autoClassifyEnabled && hasAutoOriginFiles" class="flex items-center gap-3">
        <!-- Barra de progreso (visible cuando está clasificando) -->
        <div v-if="isClassifying" class="flex items-center gap-2 min-w-[200px]">
          <div class="flex-1 h-2 bg-zinc-200 rounded-full overflow-hidden">
            <div
              class="h-full bg-violet-500 transition-all duration-300"
              :style="{ width: `${classifyProgressPercent}%` }"
            />
          </div>
          <span class="text-xs text-violet-600 font-medium whitespace-nowrap">
            {{ classifyingProgress.current }}/{{ classifyingProgress.total }}
          </span>
        </div>

        <!-- Botón Catalogar -->
        <Button
          size="sm"
          variant="outline"
          @click="emit('classify-all')"
          :disabled="isClassifying || isProcessing"
          class="text-violet-600 border-violet-300 hover:bg-violet-50"
        >
          <template v-if="isClassifying">
            <Loader2 class="w-4 h-4 mr-1 animate-spin" />
            Catalogando...
          </template>
          <template v-else>
            <Sparkles class="w-4 h-4 mr-1" />
            Catalogar todo
          </template>
        </Button>
      </div>
    </div>

    <!-- Lista de archivos -->
    <TransitionGroup name="list" tag="div" class="space-y-2 max-h-80 overflow-y-auto">
      <Card
        v-for="file in files"
        :key="file.id"
        class="transition-all duration-200"
        :class="getStatusClasses(file.status)"
      >
        <CardContent class="p-3 sm:p-4">
          <div class="flex items-center gap-3">
            <!-- Icono de estado -->
            <div class="flex-shrink-0">
              <Loader2
                v-if="file.status === 'uploading' || file.caratulaLoading"
                class="w-8 h-8 text-blue-500 animate-spin"
              />
              <CheckCircle2
                v-else-if="file.status === 'success'"
                class="w-8 h-8 text-green-500"
              />
              <XCircle
                v-else-if="file.status === 'error'"
                class="w-8 h-8 text-red-500"
              />
              <FileText
                v-else
                class="w-8 h-8 text-zinc-400"
              />
            </div>

            <!-- Información del archivo -->
            <div class="flex-1 min-w-0">
              <p class="text-sm font-medium text-zinc-800 truncate" :title="file.name">
                {{ file.name }}
              </p>
              <div class="flex items-center gap-2 mt-1">
                <span class="text-xs text-zinc-500">{{ formatSize(file.size) }}</span>

                <!-- Barra de progreso durante la subida -->
                <template v-if="file.status === 'uploading'">
                  <div class="flex-1 h-1.5 bg-zinc-200 rounded-full overflow-hidden">
                    <div
                      class="h-full bg-blue-500 transition-all duration-300"
                      :style="{ width: `${file.progress}%` }"
                    />
                  </div>
                  <span class="text-xs text-blue-600 font-medium">{{ file.progress }}%</span>
                </template>

                <!-- Mensaje de error -->
                <span v-else-if="file.status === 'error'" class="text-xs text-red-600 truncate">
                  {{ file.error }}
                </span>

                <!-- Estado de éxito con badge de origen -->
                <template v-else-if="file.status === 'success'">
                  <span class="text-xs text-green-600">Procesado</span>
                  <span
                    v-if="file.origen && file.origen !== 'auto'"
                    class="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded-full text-white"
                    :style="{ backgroundColor: getOrigenById(file.origen)?.color || '#6B7280' }"
                  >
                    {{ getOrigenById(file.origen)?.abreviacion || 'Sin clasificar' }}
                  </span>
                </template>

                <!-- Carátula extraída (si existe y está pendiente) -->
                <span
                  v-else-if="file.caratula && file.status === 'pending'"
                  class="text-xs text-zinc-400 truncate max-w-[150px]"
                  :title="file.caratula"
                >
                  {{ file.caratula }}
                </span>
              </div>
            </div>

            <!-- Selector de origen (solo para archivos pendientes o con error) -->
            <div v-if="file.status === 'pending' || file.status === 'error'" class="flex-shrink-0">
              <OriginSelect
                :model-value="file.origen"
                :origins="origins"
                :show-auto="autoClassifyEnabled"
                size="sm"
                :disabled="file.status === 'uploading' || isClassifying"
                @update:model-value="handleOrigenChange(file.id, $event)"
              />
            </div>

            <!-- Acciones -->
            <div class="flex-shrink-0 flex items-center gap-1">
              <!-- Botón reintentar (solo para errores) -->
              <Button
                v-if="file.status === 'error'"
                variant="ghost"
                size="icon"
                class="w-8 h-8 text-zinc-400 hover:text-blue-500 hover:bg-blue-50"
                @click="emit('retry', file.id)"
                title="Reintentar"
              >
                <RefreshCw class="w-4 h-4" />
              </Button>

              <!-- Botón eliminar (solo si no está subiendo) -->
              <Button
                v-if="file.status !== 'uploading'"
                variant="ghost"
                size="icon"
                class="w-8 h-8 text-zinc-400 hover:text-red-500 hover:bg-red-50"
                @click="emit('remove', file.id)"
                title="Eliminar"
              >
                <Trash2 class="w-4 h-4" />
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </TransitionGroup>

    <!-- Botones de acción -->
    <div class="flex items-center justify-end gap-3 pt-2 border-t border-zinc-200">
      <Button
        variant="outline"
        size="sm"
        @click="emit('clear')"
        :disabled="isProcessing"
        class="text-zinc-600"
      >
        <X class="w-4 h-4 mr-1" />
        Limpiar cola
      </Button>

      <Button
        size="sm"
        @click="emit('process')"
        :disabled="!canProcess"
      >
        <template v-if="isProcessing">
          <Loader2 class="w-4 h-4 mr-1 animate-spin" />
          Procesando...
        </template>
        <template v-else>
          <Play class="w-4 h-4 mr-1" />
          Procesar todos
        </template>
      </Button>
    </div>
  </div>
</template>
