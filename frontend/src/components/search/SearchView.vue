<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useDebounceFn } from '@vueuse/core'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import OriginSelect from '@/components/documents/OriginSelect.vue'
import FilePreviewModal from '@/components/shared/FilePreviewModal.vue'
import { documentsService } from '@/services/documents'
import { useOrigins } from '@/composables/useOrigins'
import {
  Search,
  FileText,
  Loader2,
  AlertCircle,
  X,
  ChevronRight,
  Scale
} from 'lucide-vue-next'

// Composable de orígenes
const { origins, fetchOrigins } = useOrigins()

// Cargar orígenes al montar
onMounted(() => {
  fetchOrigins()
})

// Estado de búsqueda
const searchQuery = ref('')
const selectedOrigenId = ref(null)
const results = ref([])
const total = ref(0)
const loading = ref(false)
const loadingMore = ref(false)
const error = ref(null)
const hasSearched = ref(false)

// Paginación
const PAGE_SIZE = 20
const currentPage = ref(0)
const hasMore = computed(() => results.value.length < total.value)

// Modal de preview
const selectedFile = ref(null)
const showPreview = ref(false)

// Referencia al sentinel para scroll infinito
const sentinelRef = ref(null)
let observer = null

// Búsqueda con debounce (400ms)
const debouncedSearch = useDebounceFn(async (query, origenId) => {
  if (query.length < 2) {
    results.value = []
    total.value = 0
    hasSearched.value = false
    return
  }

  loading.value = true
  error.value = null
  currentPage.value = 0

  try {
    const response = await documentsService.search(query, {
      skip: 0,
      limit: PAGE_SIZE,
      origenId: origenId
    })
    results.value = response.documents
    total.value = response.total
    hasSearched.value = true
  } catch (err) {
    error.value = err.userMessage || 'Error al buscar documentos'
    results.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}, 400)

// Cargar más resultados (scroll infinito)
const loadMore = async () => {
  if (loadingMore.value || !hasMore.value || searchQuery.value.length < 2) return

  loadingMore.value = true
  currentPage.value++

  try {
    const response = await documentsService.search(searchQuery.value, {
      skip: currentPage.value * PAGE_SIZE,
      limit: PAGE_SIZE,
      origenId: selectedOrigenId.value
    })
    results.value = [...results.value, ...response.documents]
  } catch (err) {
    currentPage.value--
    console.error('Error cargando más resultados:', err)
  } finally {
    loadingMore.value = false
  }
}

// Watch para ejecutar búsqueda cuando cambia query u origen
watch([searchQuery, selectedOrigenId], ([newQuery, newOrigenId]) => {
  debouncedSearch(newQuery, newOrigenId)
})

// Intersection Observer para scroll infinito
onMounted(() => {
  observer = new IntersectionObserver(
    (entries) => {
      if (entries[0].isIntersecting && hasMore.value && !loading.value) {
        loadMore()
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

// Watch para reconectar observer cuando cambia el sentinel
watch(sentinelRef, (el) => {
  if (observer && el) {
    observer.disconnect()
    observer.observe(el)
  }
})

// Limpiar búsqueda
const clearSearch = () => {
  searchQuery.value = ''
  selectedOrigenId.value = null
  results.value = []
  total.value = 0
  hasSearched.value = false
  error.value = null
}

// Abrir preview de documento
const openPreview = (doc) => {
  selectedFile.value = {
    id: doc.id,
    name: doc.caratula || doc.name,
    previewUrl: documentsService.getPreviewUrl(doc.id)
  }
  showPreview.value = true
}

// Descargar documento
const handleDownload = (file) => {
  documentsService.download(file.id, `${file.name}.pdf`)
}

// Abrir en nueva pestaña
const handleOpenExternal = (file) => {
  window.open(documentsService.getPreviewUrl(file.id), '_blank')
}

// Formatear tamaño de archivo
const formatFileSize = (bytes) => {
  if (!bytes) return ''
  const kb = bytes / 1024
  if (kb < 1024) return `${kb.toFixed(0)} KB`
  return `${(kb / 1024).toFixed(1)} MB`
}

// Extraer materia del search_content
const extractMateria = (searchContent) => {
  if (!searchContent) return null
  const match = searchContent.match(/MATERIA:\s*([^\n|]+)/i)
  return match ? match[1].trim() : null
}
</script>

<template>
  <div class="h-full flex flex-col p-4 sm:p-6 overflow-auto">
    <!-- Header -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-semibold text-zinc-800">Búsqueda de Documentos</h1>
        <p class="text-sm text-zinc-500 mt-1">
          Busca por expediente, partes, materia o cualquier texto
        </p>
      </div>
    </div>

    <!-- Search input + filtro en Card -->
    <Card class="mb-6">
      <CardContent class="p-4">
        <div class="flex flex-col sm:flex-row gap-3">
          <!-- Input de búsqueda -->
          <div class="relative flex-1">
            <Search
              class="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-zinc-400 pointer-events-none"
            />
            <Input
              v-model="searchQuery"
              type="text"
              placeholder="Buscar por nombre, expediente, partes, materia..."
              class="pl-10 pr-10 h-12 text-base"
            />
            <Transition name="fade">
              <button
                v-if="searchQuery"
                class="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-zinc-100 text-zinc-400 hover:text-zinc-600 transition-colors"
                @click="clearSearch"
              >
                <X class="w-4 h-4" />
              </button>
            </Transition>
          </div>

          <!-- Filtro de origen -->
          <div class="w-full sm:w-auto">
            <OriginSelect
              v-model="selectedOrigenId"
              :origins="origins"
              :show-all="true"
              placeholder="Todos los orígenes"
              size="lg"
              textSize="md"
            />
          </div>
        </div>

        <!-- Contador de resultados -->
        <Transition name="fade">
          <p v-if="hasSearched && !loading" class="text-sm text-zinc-500 mt-2">
            {{ total }} {{ total === 1 ? 'documento encontrado' : 'documentos encontrados' }}
          </p>
        </Transition>
      </CardContent>
    </Card>

    <!-- Contenido principal -->
    <div class="flex-1">
          
          <!-- Estado inicial -->
          <Transition name="fade" mode="out-in">
            <div 
              v-if="!hasSearched && !loading && searchQuery.length < 2"
              key="initial"
              class="flex flex-col items-center justify-center py-16 text-center"
            >
              <div class="w-14 h-14 rounded-full bg-zinc-100 flex items-center justify-center mb-6">
                <Scale class="w-7 h-7 text-zinc-400" />
              </div>
              <h2 class="text-base font-medium text-zinc-700 mb-2">
                Busca en tu biblioteca jurídica
              </h2>
              <p class="text-sm text-zinc-500 max-w-md">
                Escribe al menos 2 caracteres para buscar por expediente, 
                nombre de las partes, materia, fechas o cualquier texto del documento.
              </p>
            </div>
            
            <!-- Loading inicial -->
            <div 
              v-else-if="loading && results.length === 0"
              key="loading"
              class="flex flex-col items-center justify-center py-16"
            >
              <Loader2 class="w-10 h-10 text-zinc-400 animate-spin mb-4" />
              <p class="text-sm text-zinc-500">Buscando documentos...</p>
            </div>
            
            <!-- Error -->
            <div 
              v-else-if="error"
              key="error"
              class="flex flex-col items-center justify-center py-16 text-center"
            >
              <div class="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
                <AlertCircle class="w-7 h-7 text-red-500" />
              </div>
              <h3 class="text-base font-medium text-zinc-700 mb-2">Error en la búsqueda</h3>
              <p class="text-sm text-zinc-500 mb-4">{{ error }}</p>
              <Button variant="outline" @click="clearSearch">
                Intentar de nuevo
              </Button>
            </div>
            
            <!-- Sin resultados -->
            <div 
              v-else-if="hasSearched && results.length === 0"
              key="empty"
              class="flex flex-col items-center justify-center py-16 text-center"
            >
              <div class="w-14 h-14 rounded-full bg-zinc-100 flex items-center justify-center mb-4">
                <Search class="w-7 h-7 text-zinc-400" />
              </div>
              <h3 class="text-base font-medium text-zinc-700 mb-2">
                No se encontraron documentos
              </h3>
              <p class="text-sm text-zinc-500 max-w-md">
                No hay documentos que coincidan con "{{ searchQuery }}". 
                Prueba con otros términos de búsqueda.
              </p>
            </div>
            
            <!-- Lista de resultados -->
            <div v-else key="results" class="space-y-3">
              <TransitionGroup name="list" tag="div" class="space-y-3">
                <Card
                  v-for="doc in results"
                  :key="doc.id"
                  class="group cursor-pointer hover:shadow-md transition-all duration-200 bg-white overflow-hidden"
                  @click="openPreview(doc)"
                >
                  <CardContent class="p-4 sm:p-5">
                    <div class="flex items-start gap-4">
                      <!-- Icono -->
                      <div class="w-12 h-12 rounded-lg bg-red-50 flex items-center justify-center shrink-0">
                        <FileText class="w-6 h-6 text-red-500" />
                      </div>
                      
                      <!-- Info -->
                      <div class="flex-1 min-w-0">
                        <!-- Título -->
                        <h3 class="font-medium text-zinc-800 group-hover:text-zinc-900 truncate pr-4">
                          {{ doc.caratula || doc.name }}
                        </h3>
                        
                        <!-- Nombre original si es diferente -->
                        <p 
                          v-if="doc.caratula && doc.name !== doc.caratula" 
                          class="text-xs text-zinc-400 truncate mt-0.5"
                        >
                          {{ doc.original_filename }}
                        </p>
                        
                        <!-- Origen, Materia y metadata -->
                        <div class="flex flex-wrap items-center gap-2 mt-2">
                          <!-- Badge de origen -->
                          <span
                            v-if="doc.origen"
                            class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs font-medium"
                            :style="{
                              backgroundColor: doc.origen.color + '15',
                              color: doc.origen.color
                            }"
                          >
                            <span
                              class="w-1.5 h-1.5 rounded-full"
                              :style="{ backgroundColor: doc.origen.color }"
                            />
                            {{ doc.origen.abreviacion }}
                          </span>
                          <span
                            v-if="extractMateria(doc.search_content)"
                            class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-50 text-blue-700"
                          >
                            {{ extractMateria(doc.search_content) }}
                          </span>
                          <span
                            v-if="doc.chunks_count"
                            class="text-xs text-zinc-400"
                          >
                            {{ doc.chunks_count }} fragmentos
                          </span>
                          <span
                            v-if="doc.file_size"
                            class="text-xs text-zinc-400"
                          >
                            {{ formatFileSize(doc.file_size) }}
                          </span>
                        </div>
                      </div>
                      
                      <!-- Flecha -->
                      <ChevronRight 
                        class="w-5 h-5 text-zinc-300 group-hover:text-zinc-500 group-hover:translate-x-1 transition-all shrink-0 mt-1" 
                      />
                    </div>
                  </CardContent>
                </Card>
              </TransitionGroup>
              
              <!-- Sentinel para scroll infinito -->
              <div ref="sentinelRef" class="h-4" />
              
              <!-- Loading more -->
              <Transition name="fade">
                <div 
                  v-if="loadingMore" 
                  class="flex justify-center py-4"
                >
                  <Loader2 class="w-6 h-6 text-zinc-400 animate-spin" />
                </div>
              </Transition>
              
              <!-- Fin de resultados -->
              <Transition name="fade">
                <p 
                  v-if="!hasMore && results.length > PAGE_SIZE" 
                  class="text-center text-sm text-zinc-400 py-4"
                >
                  Has llegado al final de los resultados
                </p>
              </Transition>
            </div>
          </Transition>
    </div>

    <!-- Modal de preview -->
    <FilePreviewModal
      v-model:open="showPreview"
      :file="selectedFile"
      @download="handleDownload"
      @open-external="handleOpenExternal"
    />
  </div>
</template>
