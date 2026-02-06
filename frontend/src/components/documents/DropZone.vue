<script setup>
import { ref, computed } from 'vue'
import { CloudUpload } from 'lucide-vue-next'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['files-dropped'])

const isDragging = ref(false)

const handleDragOver = (event) => {
  if (props.disabled) return
  event.preventDefault()
  isDragging.value = true
}

const handleDragLeave = () => {
  isDragging.value = false
}

const handleDrop = (event) => {
  if (props.disabled) return
  event.preventDefault()
  isDragging.value = false
  
  const files = Array.from(event.dataTransfer.files)
  // Filtrar solo PDFs
  const pdfFiles = files.filter(f => f.name.toLowerCase().endsWith('.pdf'))
  if (pdfFiles.length > 0) {
    emit('files-dropped', pdfFiles)
  }
}

const handleClick = () => {
  if (props.disabled) return
  
  const input = document.createElement('input')
  input.type = 'file'
  input.multiple = true
  input.accept = '.pdf'
  input.onchange = (e) => {
    const files = Array.from(e.target.files)
    if (files.length > 0) {
      emit('files-dropped', files)
    }
  }
  input.click()
}
</script>

<template>
  <div
    class="
      border-2 border-dashed rounded-xl
      flex flex-col items-center justify-center
      transition-all duration-200
      p-6 sm:p-8
    "
    :class="[
      disabled 
        ? 'border-zinc-200 bg-zinc-50 cursor-not-allowed opacity-60'
        : isDragging
          ? 'border-[#d3a779] bg-[#d3a779]/5 cursor-pointer'
          : 'border-zinc-300 hover:border-zinc-400 bg-white cursor-pointer'
    ]"
    @dragover="handleDragOver"
    @dragleave="handleDragLeave"
    @drop="handleDrop"
    @click="handleClick"
  >
    <CloudUpload 
      class="text-zinc-400 mb-4 transition-colors"
      :class="[
        isDragging ? 'text-[#d3a779]' : 'text-zinc-400',
        'w-12 h-12 sm:w-14 sm:h-14 lg:w-16 lg:h-16'
      ]"
    />
    <p 
      class="text-center font-medium transition-colors text-sm sm:text-base"
      :class="isDragging ? 'text-[#d3a779]' : 'text-zinc-600'"
    >
      Arrastra tus sentencias PDF aquí
    </p>
    <p class="text-zinc-400 text-xs sm:text-sm mt-2">
      o haz clic para seleccionar archivos
    </p>
  </div>
</template>
