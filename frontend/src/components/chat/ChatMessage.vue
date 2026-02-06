<script setup>
import { computed } from 'vue'
import { Bot, User } from 'lucide-vue-next'
import ChatFileAttachment from './ChatFileAttachment.vue'

const props = defineProps({
  message: {
    type: Object,
    required: true,
    validator: (value) => 'id' in value && 'role' in value && 'content' in value
  }
})

const emit = defineEmits(['file-click'])

const isUser = computed(() => props.message.role === 'user')
const hasFiles = computed(() => props.message.files && props.message.files.length > 0)

const containerClasses = computed(() => [
  'flex gap-2 items-start',
  isUser.value ? 'flex-row-reverse' : 'flex-row'
])

const bubbleClasses = computed(() => [
  'rounded-2xl px-4 py-3 max-w-[85%] md:max-w-[70%]',
  isUser.value
    ? 'bg-zinc-700 text-white rounded-tr-md'
    : 'bg-white text-zinc-900 border border-zinc-200 rounded-tl-md'
])

const avatarClasses = computed(() => [
  'w-8 h-8 rounded-full flex items-center justify-center shrink-0',
  isUser.value ? 'bg-zinc-700' : 'bg-zinc-300'
])

const contentClasses = computed(() => [
  'flex flex-col flex-1 min-w-0',
  isUser.value ? 'items-end' : 'items-start'
])

const handleFileClick = (file) => {
  emit('file-click', file)
}
</script>

<template>
  <div :class="containerClasses">
    <!-- Avatar -->
    <div :class="avatarClasses">
      <User v-if="isUser" class="w-4 h-4 text-white" />
      <Bot v-else class="w-4 h-4 text-zinc-600" />
    </div>
    
    <!-- Contenido del mensaje -->
    <div :class="contentClasses">
      <!-- Burbuja del mensaje -->
      <div :class="bubbleClasses">
        <p class="text-sm sm:text-base whitespace-pre-wrap break-words">
          {{ message.content }}
        </p>
      </div>
      
      <!-- Archivos adjuntos (solo para mensajes de IA) -->
      <div 
        v-if="hasFiles && !isUser" 
        class="flex flex-col gap-2 mt-1"
      >
        <p class="text-xs text-zinc-500 font-medium px-1">
          Documentos relacionados:
        </p>
        <div class="grid gap-2 grid-cols-1 sm:grid-cols-2">
          <ChatFileAttachment
            v-for="file in message.files"
            :key="file.id"
            :file="file"
            @click="handleFileClick(file)"
          />
        </div>
      </div>
    </div>
  </div>
</template>
