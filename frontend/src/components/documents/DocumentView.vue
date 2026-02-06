<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import DropZone from './DropZone.vue'
import FileCard from './FileCard.vue'
import UploadQueue from './UploadQueue.vue'
import OriginSelect from './OriginSelect.vue'
import FilePreviewModal from '@/components/shared/FilePreviewModal.vue'
import { Card, CardContent } from '@/components/ui/card'
import { useDocuments } from '@/composables/useDocuments'
import { useOrigins } from '@/composables/useOrigins'
import { Loader2, FileText, AlertCircle, X } from 'lucide-vue-next'

// Usar el composable de documentos
const {
  documents,
  loading,
  loadingMore,
  error,
  total,
  hasMore,
  // Estado de cola
  pendingFiles,
  isProcessingQueue,
  hasPendingFiles,
  canProcessQueue,
  // Métodos
  fetchDocuments,
  loadMoreDocuments,
  deleteDocument,
  downloadDocument,
  getPreviewUrl,
  clearError,
  // Métodos de cola
  addFilesToQueue,
  removeFromQueue,
  clearQueue,
  processQueue,
  retryFile,
  updateFileOrigen,
  updateFileCaratula,
  setFileCaratulaLoading
} = useDocuments()

// Usar el composable de orígenes
const {
  origins,
  isClassifying,
  classifyingProgress,
  fetchOrigins,
  classifyBatch,
  classifyOneByOne,
  extractCaratula
} = useOrigins()

// Estado del modal
const isPreviewOpen = ref(false)
const selectedFile = ref(null)

// Estado de clasificación automática
const autoClassifyEnabled = ref(false)
const selectedGlobalOrigen = ref(null)

// Referencia al sentinel para scroll infinito
const sentinelRef = ref(null)
let observer = null

// Cargar documentos y orígenes al montar el componente
onMounted(() => {
  fetchDocuments()
  fetchOrigins()

  // Configurar IntersectionObserver para scroll infinito
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loading.value && !loadingMore.value) {
        loadMoreDocuments()
      }
    },
    { rootMargin: '100px' }
  )

  if (sentinelRef.value) {
    observer.observe(sentinelRef.value)
  }
})

onUnmounted(() => {
  if (observer) {
    observer.disconnect()
  }
})

// Reconectar observer cuando cambia el sentinel
watch(sentinelRef, (el) => {
  if (observer && el) {
    observer.disconnect()
    observer.observe(el)
  }
})

const handleFilesDropped = async (droppedFiles) => {
  // Filtrar solo archivos PDF válidos
  const validFiles = droppedFiles.filter(file => {
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      console.warn(`Archivo ignorado (no es PDF): ${file.name}`)
      return false
    }
    return true
  })

  if (validFiles.length > 0) {
    // Determinar el origen por defecto
    const defaultOrigen = autoClassifyEnabled.value ? 'auto' : selectedGlobalOrigen.value

    // Agregar archivos a la cola
    addFilesToQueue(validFiles, defaultOrigen)

    // Si está en modo auto, extraer carátulas en background
    if (autoClassifyEnabled.value) {
      for (const file of validFiles) {
        // Encontrar el item en la cola (por nombre, ya que el id se asigna en addFilesToQueue)
        const queueItem = pendingFiles.value.find(
          f => f.name === file.name && f.status === 'pending'
        )
        if (queueItem) {
          setFileCaratulaLoading(queueItem.id, true)
          const caratula = await extractCaratula(file)
          updateFileCaratula(queueItem.id, caratula)
        }
      }
    }
  }
}

const handleDeleteFile = async (fileId) => {
  if (confirm('¿Estás seguro de eliminar este documento?')) {
    await deleteDocument(fileId)
  }
}

const handleOpenFile = (file) => {
  selectedFile.value = {
    ...file,
    previewUrl: getPreviewUrl(file.id)
  }
  isPreviewOpen.value = true
}

const handleDownload = (file) => {
  downloadDocument(file.id, file.original_filename || file.name + '.pdf')
}

const handleOpenExternal = (file) => {
  // Abrir en nueva pestaña
  window.open(getPreviewUrl(file.id), '_blank')
}

// Handler para actualizar origen de un archivo en la cola
const handleUpdateOrigen = (fileId, origen) => {
  updateFileOrigen(fileId, origen)
}

// Handler para clasificar todos los archivos con origen 'auto'
const handleClassifyAll = async () => {
  // Obtener archivos pendientes con origen 'auto' y carátula
  const filesToClassify = pendingFiles.value
    .filter(f => f.status === 'pending' && f.origen === 'auto')
    .map(f => ({
      id: f.id,
      caratula: f.caratula || f.name // Usar nombre si no hay carátula
    }))

  if (filesToClassify.length === 0) return

  // Clasificar uno por uno con callback de progreso
  await classifyOneByOne(filesToClassify, (result, current, total) => {
    // Actualizar origen inmediatamente después de clasificar cada archivo
    updateFileOrigen(result.id, result.origen_id)
  })
}
</script>

<template>
  <div class="h-full flex flex-col p-4 sm:p-6 overflow-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-semibold text-zinc-800">Biblioteca</h1>
        <p class="text-sm text-zinc-500 mt-1">
          {{ total }} archivo{{ total !== 1 ? 's' : '' }} en tu biblioteca
        </p>
      </div>
    </div>

    <!-- Controles de clasificación -->
    <section class="mb-4 sm:mb-6">
      <Card>
        <CardContent class="flex flex-wrap items-center gap-4 p-3">
        <!-- Checkbox de clasificación automática -->
        <label class="flex items-center gap-2 cursor-pointer select-none">
          <input
            type="checkbox"
            v-model="autoClassifyEnabled"
            class="w-4 h-4 text-blue-600 border-zinc-300 rounded focus:ring-blue-500"
          />
          <span class="text-sm font-medium text-zinc-700">Elección automática</span>
        </label>

        <!-- Advertencia de tiempo (solo si está activado) -->
        <span
          v-if="autoClassifyEnabled"
          class="text-xs text-amber-600 bg-amber-50 px-2 py-1 rounded"
        >
          La clasificación con IA puede demorar
        </span>

        <!-- Selector global de origen (solo en modo manual) -->
        <div v-if="!autoClassifyEnabled" class="flex items-center gap-2 ml-auto">
          <span class="text-sm text-zinc-500">Origen:</span>
          <OriginSelect
            v-model="selectedGlobalOrigen"
            :origins="origins"
            :show-auto="false"
            size="md"
            placeholder="Seleccionar..."
          />
        </div>
        </CardContent>
      </Card>
    </section>

    <!-- Zona de Drop -->
    <section class="mb-6 sm:mb-8">
      <DropZone
        @files-dropped="handleFilesDropped"
        :disabled="isProcessingQueue"
      />

      <!-- Cola de archivos pendientes -->
      <Transition name="slide-down">
        <div v-if="hasPendingFiles" class="mt-4">
          <UploadQueue
            :files="pendingFiles"
            :origins="origins"
            :is-processing="isProcessingQueue"
            :can-process="canProcessQueue"
            :auto-classify-enabled="autoClassifyEnabled"
            :is-classifying="isClassifying"
            :classifying-progress="classifyingProgress"
            @remove="removeFromQueue"
            @retry="retryFile"
            @process="processQueue"
            @clear="clearQueue"
            @update-origen="handleUpdateOrigen"
            @classify-all="handleClassifyAll"
          />
        </div>
      </Transition>
    </section>

    <!-- Mensaje de error -->
    <Transition name="slide-down">
      <div
        v-if="error"
        class="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg flex items-center justify-between"
      >
        <div class="flex items-center gap-2">
          <AlertCircle class="w-4 h-4 text-red-500 shrink-0" />
          <span class="text-red-700 text-sm">{{ error }}</span>
        </div>
        <button
          @click="clearError"
          class="text-red-400 hover:text-red-600"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </Transition>

    <!-- Separador antes de la grilla -->

    <!-- Estados: carga, grilla, vacío -->
    <Transition name="fade" mode="out-in">
      <!-- Estado de carga -->
      <section v-if="loading && documents.length === 0" key="loading" class="flex-1 flex items-center justify-center">
        <div class="flex flex-col items-center">
          <Loader2 class="w-10 h-10 text-zinc-400 animate-spin mb-4" />
          <p class="text-zinc-500">Cargando documentos...</p>
        </div>
      </section>

      <!-- Grilla de archivos -->
      <section
        v-else-if="documents.length > 0"
        key="grid"
      >
        <TransitionGroup
          name="list"
          tag="div"
          class="grid gap-3 sm:gap-4 grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4"
        >
          <FileCard
            v-for="file in documents"
            :key="file.id"
            :file="file"
            @click="handleOpenFile(file)"
            @delete="handleDeleteFile(file.id)"
          />
        </TransitionGroup>

        <!-- Sentinel para scroll infinito -->
        <div ref="sentinelRef" class="h-4" />

        <!-- Indicador de cargando más -->
        <Transition name="fade">
          <div
            v-if="loadingMore"
            class="flex justify-center py-6"
          >
            <Loader2 class="w-6 h-6 text-zinc-400 animate-spin" />
          </div>
        </Transition>

        <!-- Mensaje de fin de lista -->
        <Transition name="fade">
          <p
            v-if="!hasMore && documents.length > 50"
            class="text-center text-sm text-zinc-400 py-4"
          >
            Has llegado al final de la lista
          </p>
        </Transition>
      </section>

      <!-- Estado vacío -->
      <section
        v-else
        key="empty"
        class="flex-1 flex flex-col items-center justify-center text-center py-12"
      >
        <div class="w-14 h-14 rounded-full bg-zinc-100 flex items-center justify-center mb-4">
          <FileText class="w-7 h-7 text-zinc-400" />
        </div>
        <h3 class="text-base font-medium text-zinc-700 mb-2">
          Sin documentos
        </h3>
        <p class="text-sm text-zinc-500 max-w-sm">
          Arrastra archivos PDF a la zona superior o haz clic para comenzar a construir tu biblioteca.
        </p>
      </section>
    </Transition>

    <!-- Modal de previsualización -->
    <FilePreviewModal
      v-model:open="isPreviewOpen"
      :file="selectedFile"
      @download="handleDownload"
      @open-external="handleOpenExternal"
    />
  </div>
</template>
