<script setup>
import { ref, nextTick, watch } from 'vue'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Card } from '@/components/ui/card'
import ChatMessage from './ChatMessage.vue'
import ChatInput from './ChatInput.vue'
import FilePreviewModal from '@/components/shared/FilePreviewModal.vue'
import { useChat } from '@/composables/useChat'
import { useDocuments } from '@/composables/useDocuments'
import { Loader2, Bot, MessageSquare, AlertCircle, X } from 'lucide-vue-next'

// Usar composables
const { 
  messages, 
  loading, 
  error, 
  sendMessage, 
  clearError 
} = useChat()

const { getPreviewUrl } = useDocuments()

const scrollAreaRef = ref(null)

/**
 * Hace scroll hacia el fondo del área de mensajes.
 * @param {boolean} smooth - Si true, usa animación suave
 * @param {number} delay - Delay en ms antes de hacer scroll (para esperar renderizado)
 */
const scrollToBottom = (smooth = true, delay = 50) => {
  setTimeout(() => {
    if (scrollAreaRef.value) {
      const viewport = scrollAreaRef.value.$el?.querySelector('[data-radix-scroll-area-viewport]')
      if (viewport) {
        viewport.scrollTo({
          top: viewport.scrollHeight,
          behavior: smooth ? 'smooth' : 'instant'
        })
      }
    }
  }, delay)
}

// Scroll al fondo cuando se agregan nuevos mensajes
watch(
  () => messages.value.length,
  (newCount, oldCount) => {
    if (newCount > oldCount) {
      // Nuevo mensaje agregado - scroll suave hacia abajo
      nextTick(() => {
        scrollToBottom(true, 100)
      })
    }
  }
)

// Scroll cuando aparece o desaparece el indicador de carga
watch(loading, (isLoading, wasLoading) => {
  // Scroll cuando empieza a cargar (muestra "Analizando documentos...")
  if (isLoading) {
    nextTick(() => {
      scrollToBottom(true, 100)
    })
  }
  // Scroll suave cuando termina de cargar (transición de "Analizando" a respuesta final)
  if (wasLoading && !isLoading) {
    // Delay más largo para asegurar que la respuesta y archivos se renderizaron completamente
    nextTick(() => {
      scrollToBottom(true, 200)
    })
  }
})

const handleSendMessage = async (content) => {
  // Scroll inmediato cuando el usuario envía un mensaje
  // (el watcher de messages.length se encargará del scroll automático)
  await sendMessage(content)
}

// Estado del modal de previsualización
const isPreviewOpen = ref(false)
const selectedFile = ref(null)

const handleFileClick = (file) => {
  // Usar documentId para obtener la URL de preview del documento real
  const docId = file.documentId || file.id
  selectedFile.value = {
    ...file,
    id: docId,
    // Agregar URL de preview usando el documentId
    previewUrl: docId ? getPreviewUrl(docId) : null
  }
  isPreviewOpen.value = true
}

const handleDownload = (file) => {
  if (file.previewUrl) {
    // Crear enlace de descarga
    const link = document.createElement('a')
    link.href = file.previewUrl
    link.download = file.name || 'documento.pdf'
    document.body.appendChild(link)
    link.click()
    link.remove()
  }
}

const handleOpenExternal = (file) => {
  if (file.previewUrl) {
    window.open(file.previewUrl, '_blank')
  }
}
</script>

<template>
  <div class="h-full flex flex-col p-4 sm:p-6 overflow-hidden">
    <!-- Header del chat -->
    <div class="flex items-center justify-between mb-6">
      <div>
        <h1 class="text-lg font-semibold text-zinc-800">Asistente Jurídico</h1>
        <p class="text-sm text-zinc-500 mt-1">
          Consulta sobre tus documentos y jurisprudencia
        </p>
      </div>
    </div>

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

    <!-- Chat area (mensajes + input) en Card -->
    <Card class="flex-1 flex flex-col overflow-hidden">
      <!-- Área de mensajes -->
      <ScrollArea ref="scrollAreaRef" class="flex-1">
        <div class="p-4 sm:p-6 max-w-4xl mx-auto">
        <!-- Lista de mensajes con animación -->
        <TransitionGroup name="slide-up" tag="div" class="space-y-4 sm:space-y-6">
          <ChatMessage
            v-for="message in messages"
            :key="message.id"
            :message="message"
            @file-click="handleFileClick"
          />
        </TransitionGroup>
        
        <!-- Indicador de carga -->
        <Transition name="fade">
          <div v-if="loading" class="flex items-start gap-3 mt-4 sm:mt-6">
            <div class="w-8 h-8 rounded-full bg-zinc-300 flex items-center justify-center flex-shrink-0">
              <Bot class="w-4 h-4 text-zinc-600" />
            </div>
            <div class="flex-1 mt-2">
              <div class="flex items-center gap-2">
                <Loader2 class="w-4 h-4 text-zinc-400 animate-spin" />
                <span class="text-sm text-zinc-500">Analizando documentos...</span>
              </div>
            </div>
          </div>
        </Transition>
        
        <!-- Estado vacío si no hay mensajes -->
        <Transition name="fade">
          <div 
            v-if="messages.length === 0 && !loading" 
            class="flex flex-col items-center justify-center py-12 text-center"
          >
            <div class="w-14 h-14 rounded-full bg-zinc-100 flex items-center justify-center mb-4">
              <MessageSquare class="w-7 h-7 text-zinc-400" />
            </div>
            <h3 class="text-base font-medium text-zinc-700 mb-2">
              Inicia una conversación
            </h3>
            <p class="text-sm text-zinc-500 max-w-sm">
              Escribe tu pregunta sobre jurisprudencia o los documentos de tu biblioteca.
            </p>
          </div>
        </Transition>
      </div>
    </ScrollArea>

    <!-- Input de envío -->
    <ChatInput
      @send="handleSendMessage"
      :disabled="loading"
    />
    </Card>

    <!-- Modal de previsualización -->
    <FilePreviewModal
      v-model:open="isPreviewOpen"
      :file="selectedFile"
      @download="handleDownload"
      @open-external="handleOpenExternal"
    />
  </div>
</template>
