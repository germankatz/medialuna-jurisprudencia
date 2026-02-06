<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { ClipboardCheck, ChevronRight, CheckCircle2, FileText, Loader2, Keyboard } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import OriginSelect from '@/components/documents/OriginSelect.vue'
import { documentsService } from '@/services/documents'
import { originsService } from '@/services/origins'
import { useOrigins } from '@/composables/useOrigins'

// Composable de orígenes
const { origins, fetchOrigins } = useOrigins()

// Estado
const unclassifiedDocuments = ref([])
const currentIndex = ref(0)
const selectedOrigenId = ref(null)
const isLoading = ref(false)
const isSubmitting = ref(false)
const error = ref(null)
const showShortcutsHelp = ref(false)

// Documento actual
const currentDocument = computed(() => {
  if (currentIndex.value < unclassifiedDocuments.value.length) {
    return unclassifiedDocuments.value[currentIndex.value]
  }
  return null
})

// URL del preview
const previewUrl = computed(() => {
  if (currentDocument.value) {
    return documentsService.getPreviewUrl(currentDocument.value.id)
  }
  return null
})

// Contador de restantes
const remaining = computed(() => {
  return unclassifiedDocuments.value.length - currentIndex.value
})

// Orígenes filtrados (sin "sin clasificar")
const filteredOrigins = computed(() => {
  return origins.value.filter(o => o.codigo !== 'sin_clasificar' && o.activo)
})

// Origen seleccionado
const selectedOrigen = computed(() => {
  if (!selectedOrigenId.value) return null
  return origins.value.find(o => o.id === selectedOrigenId.value)
})

// Cargar datos iniciales
const loadData = async () => {
  isLoading.value = true
  error.value = null

  try {
    // Cargar orígenes
    await fetchOrigins()

    // Cargar TODOS los documentos y filtrar manualmente por "sin_clasificar"
    const result = await documentsService.getAll({ limit: 1000 })

    // Filtrar solo los que tienen origen "sin_clasificar"
    unclassifiedDocuments.value = result.documents.filter(
      doc => doc.origen && doc.origen.codigo === 'sin_clasificar'
    )

    console.log('Documentos sin clasificar encontrados:', unclassifiedDocuments.value.length)

    // Resetear índice
    currentIndex.value = 0
    selectedOrigenId.value = null

  } catch (err) {
    console.error('Error cargando datos:', err)
    error.value = err.userMessage || 'Error al cargar los datos'
  } finally {
    isLoading.value = false
  }
}

// Confirmar clasificación
const handleConfirm = async () => {
  if (!selectedOrigenId.value || !currentDocument.value || isSubmitting.value) {
    return
  }

  isSubmitting.value = true
  error.value = null

  try {
    await documentsService.updateOrigen(
      currentDocument.value.id,
      selectedOrigenId.value
    )

    // Pasar al siguiente documento
    currentIndex.value++
    selectedOrigenId.value = null

    // Si no hay más documentos, recargar
    if (currentIndex.value >= unclassifiedDocuments.value.length) {
      await loadData()
    }

  } catch (err) {
    console.error('Error clasificando documento:', err)
    error.value = err.userMessage || 'Error al clasificar el documento'
  } finally {
    isSubmitting.value = false
  }
}

// Omitir documento
const handleSkip = () => {
  if (isSubmitting.value) return

  currentIndex.value++
  selectedOrigenId.value = null

  if (currentIndex.value >= unclassifiedDocuments.value.length) {
    currentIndex.value = 0
  }
}

// Keyboard shortcuts
const handleKeydown = (event) => {
  // Ignorar si estamos escribiendo en un input
  if (event.target.tagName === 'INPUT' || event.target.tagName === 'TEXTAREA' || event.target.tagName === 'SELECT') {
    return
  }

  // No hacer nada si no hay documento actual o si está cargando
  if (!currentDocument.value || isLoading.value || isSubmitting.value) {
    return
  }

  // Números 1-9 para seleccionar orígenes
  if (event.key >= '1' && event.key <= '9') {
    const index = parseInt(event.key) - 1
    if (index < filteredOrigins.value.length) {
      selectedOrigenId.value = filteredOrigins.value[index].id
      event.preventDefault()
    }
  }
  // Enter para confirmar
  else if (event.key === 'Enter') {
    handleConfirm()
    event.preventDefault()
  }
  // Espacio o flecha derecha para omitir
  else if (event.key === ' ' || event.key === 'ArrowRight') {
    handleSkip()
    event.preventDefault()
  }
  // Escape para deseleccionar
  else if (event.key === 'Escape') {
    selectedOrigenId.value = null
    event.preventDefault()
  }
  // ? para mostrar ayuda
  else if (event.key === '?') {
    showShortcutsHelp.value = !showShortcutsHelp.value
    event.preventDefault()
  }
}

onMounted(() => {
  loadData()
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>

<template>
  <div class="h-full flex flex-col p-4 sm:p-6 overflow-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-semibold text-zinc-800">Clasificar Sentencias</h1>
        <p class="text-sm text-zinc-500 mt-1">
          Asigna un origen a las sentencias sin clasificar
        </p>
      </div>

      <!-- Contador y ayuda -->
      <div class="flex items-center gap-3 shrink-0">
        <!-- Botón de ayuda -->
        <button
          v-if="currentDocument"
          @click="showShortcutsHelp = !showShortcutsHelp"
          class="p-2 rounded-lg hover:bg-zinc-100 text-zinc-500 hover:text-zinc-700 transition-colors"
          title="Atajos de teclado (?)"
        >
          <Keyboard class="w-4 h-4 sm:w-5 sm:h-5" />
        </button>

        <!-- Contador -->
        <div v-if="!isLoading && remaining > 0" class="text-right">
          <div class="text-xl font-bold text-[#d3a779]">
            {{ remaining }}
          </div>
          <div class="text-xs text-zinc-500">
            {{ remaining === 1 ? 'restante' : 'restantes' }}
          </div>
        </div>
      </div>
    </div>

    <!-- Ayuda de shortcuts (colapsable) -->
    <Transition name="slide-down">
      <div v-if="showShortcutsHelp" class="mb-4 p-3 bg-zinc-50 rounded-lg border border-zinc-200">
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
          <div class="flex items-center gap-2">
            <kbd class="px-2 py-1 bg-zinc-100 rounded border border-zinc-300 font-mono">1-9</kbd>
            <span class="text-zinc-600">Seleccionar origen</span>
          </div>
          <div class="flex items-center gap-2">
            <kbd class="px-2 py-1 bg-zinc-100 rounded border border-zinc-300 font-mono">Enter</kbd>
            <span class="text-zinc-600">Confirmar</span>
          </div>
          <div class="flex items-center gap-2">
            <kbd class="px-2 py-1 bg-zinc-100 rounded border border-zinc-300 font-mono">Espacio</kbd>
            <span class="text-zinc-600">Omitir</span>
          </div>
          <div class="flex items-center gap-2">
            <kbd class="px-2 py-1 bg-zinc-100 rounded border border-zinc-300 font-mono">Esc</kbd>
            <span class="text-zinc-600">Deseleccionar</span>
          </div>
          <div class="flex items-center gap-2">
            <kbd class="px-2 py-1 bg-zinc-100 rounded border border-zinc-300 font-mono">?</kbd>
            <span class="text-zinc-600">Ayuda</span>
          </div>
        </div>
      </div>
    </Transition>

    <!-- Contenido -->
    <div class="flex-1 overflow-hidden">
      <!-- Loading -->
      <div v-if="isLoading" class="h-full flex items-center justify-center">
        <div class="text-center">
          <Loader2 class="w-8 h-8 text-zinc-400 animate-spin mx-auto mb-4" />
          <p class="text-zinc-600">Cargando documentos...</p>
        </div>
      </div>

      <!-- Sin documentos -->
      <div v-else-if="!currentDocument" class="h-full flex items-center justify-center">
        <div class="text-center max-w-md px-6">
          <div class="w-16 h-16 rounded-full bg-green-50 flex items-center justify-center mx-auto mb-4">
            <CheckCircle2 class="w-8 h-8 text-green-600" />
          </div>
          <h2 class="text-xl font-semibold text-zinc-900 mb-2">
            ¡Todo clasificado!
          </h2>
          <p class="text-zinc-600 mb-4">
            No hay documentos sin clasificar en este momento.
          </p>
          <Button @click="loadData" variant="outline">
            Recargar
          </Button>
        </div>
      </div>

      <!-- Vista de clasificación -->
      <div v-else class="h-full flex flex-col lg:flex-row gap-4 sm:gap-6">
        <!-- Panel izquierdo: Preview del PDF -->
        <div class="flex-1 min-h-[300px] sm:min-h-[400px] lg:min-h-0">
          <Card class="h-full overflow-hidden">
            <div class="h-full flex flex-col">
              <!-- Info del documento -->
              <div class="px-3 sm:px-4 py-2 sm:py-3 border-b">
                <div class="flex items-center gap-2 text-xs sm:text-sm text-zinc-600">
                  <FileText class="w-3 h-3 sm:w-4 sm:h-4 shrink-0" />
                  <span class="truncate font-medium">{{ currentDocument.name }}</span>
                </div>
                <div v-if="currentDocument.caratula" class="mt-1 text-xs text-zinc-500 line-clamp-2">
                  {{ currentDocument.caratula }}
                </div>
              </div>

              <!-- Preview -->
              <div class="flex-1 overflow-hidden">
                <iframe
                  v-if="previewUrl"
                  :src="previewUrl"
                  class="w-full h-full border-0"
                  title="Vista previa del documento"
                />
              </div>
            </div>
          </Card>
        </div>

        <!-- Panel derecho: Selección de origen -->
        <div class="lg:w-96 shrink-0">
          <Card class="p-4 sm:p-6">
            <h3 class="text-base sm:text-lg font-semibold text-zinc-900 mb-4">
              Seleccionar Origen
            </h3>

            <!-- Lista de orígenes con shortcuts -->
            <div class="mb-6 space-y-2">
              <label class="text-sm font-medium text-zinc-700 mb-2 block">
                Origen del documento
              </label>

              <!-- Orígenes con números -->
              <div class="space-y-1">
                <button
                  v-for="(origen, index) in filteredOrigins.slice(0, 9)"
                  :key="origen.id"
                  @click="selectedOrigenId = origen.id"
                  :disabled="isSubmitting"
                  class="w-full flex items-center gap-3 p-3 rounded-lg border transition-all"
                  :class="[
                    selectedOrigenId === origen.id
                      ? 'border-blue-500 bg-blue-50'
                      : 'border-zinc-200 hover:border-zinc-300 hover:bg-zinc-50'
                  ]"
                >
                  <!-- Número de atajo -->
                  <div class="flex items-center gap-2 shrink-0">
                    <kbd class="px-1.5 py-0.5 bg-zinc-100 rounded border border-zinc-300 font-mono text-xs">
                      {{ index + 1 }}
                    </kbd>
                    <div
                      class="w-3 h-3 rounded-full"
                      :style="{ backgroundColor: origen.color }"
                    ></div>
                  </div>

                  <!-- Info del origen -->
                  <div class="text-left min-w-0 flex-1">
                    <div class="font-medium text-sm text-zinc-900 truncate">
                      {{ origen.abreviacion }}
                    </div>
                    <div class="text-xs text-zinc-500 truncate">
                      {{ origen.nombre }}
                    </div>
                  </div>
                </button>
              </div>

              <!-- Fallback select si hay más de 9 orígenes -->
              <div v-if="filteredOrigins.length > 9" class="pt-2">
                <OriginSelect
                  v-model="selectedOrigenId"
                  :origins="filteredOrigins"
                  placeholder="Más orígenes..."
                  size="lg"
                  textSize="md"
                  :disabled="isSubmitting"
                />
              </div>
            </div>

            <!-- Error -->
            <div v-if="error" class="mb-4 p-3 rounded-lg bg-red-50 border border-red-200">
              <p class="text-sm text-red-700">{{ error }}</p>
            </div>

            <!-- Botones -->
            <div class="flex flex-col gap-2">
              <Button
                @click="handleConfirm"
                :disabled="!selectedOrigenId || isSubmitting"
                class="w-full"
              >
                <Loader2 v-if="isSubmitting" class="w-4 h-4 mr-2 animate-spin" />
                <CheckCircle2 v-else class="w-4 h-4 mr-2" />
                <span class="hidden sm:inline">{{ isSubmitting ? 'Guardando...' : 'Confirmar y Continuar' }}</span>
                <span class="sm:hidden">{{ isSubmitting ? 'Guardando...' : 'Confirmar' }}</span>
                <span class="text-sm text-gray-600">(Enter)</span> 
              </Button>

              <Button
                @click="handleSkip"
                variant="outline"
                :disabled="isSubmitting"
                class="w-full"
              >
                Omitir
                <ChevronRight class="w-4 h-4 ml-2" />
              </Button>
            </div>

            <!-- Info adicional -->
            <div class="mt-4 sm:mt-6 pt-4 sm:pt-6 border-t">
              <div class="text-xs text-zinc-500 space-y-1">
                <div class="flex justify-between gap-2">
                  <span>Documento:</span>
                  <span class="font-medium">{{ currentIndex + 1 }} de {{ unclassifiedDocuments.length }}</span>
                </div>
                <div class="flex justify-between gap-2">
                  <span>Archivo:</span>
                  <span class="font-medium truncate text-right">{{ currentDocument.original_filename }}</span>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.slide-down-enter-active,
.slide-down-leave-active {
  transition: all 0.3s ease;
}
.slide-down-enter-from,
.slide-down-leave-to {
  opacity: 0;
  transform: translateY(-10px);
  max-height: 0;
}
.slide-down-enter-to,
.slide-down-leave-from {
  max-height: 200px;
}
</style>
