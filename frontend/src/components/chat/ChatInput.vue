<script setup>
import { ref, computed } from 'vue'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Send } from 'lucide-vue-next'

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['send'])

const inputValue = ref('')

const isDisabled = computed(() => props.disabled || !inputValue.value.trim())

const handleSubmit = () => {
  if (props.disabled) return
  
  const trimmedValue = inputValue.value.trim()
  if (trimmedValue) {
    emit('send', trimmedValue)
    inputValue.value = ''
  }
}

const handleKeydown = (event) => {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault()
    handleSubmit()
  }
}
</script>

<template>
  <div class="border-t border-zinc-200 bg-white p-3 sm:p-4">
    <form 
      class="flex gap-2 sm:gap-3 items-center max-w-4xl mx-auto"
      @submit.prevent="handleSubmit"
    >
      <Input
        v-model="inputValue"
        type="text"
        placeholder="Escribe tu mensaje..."
        class="flex-1 h-10 sm:h-11 text-sm sm:text-base border-0 ring-0 focus:ring-0 focus-visible:ring-0 shadow-none"
        :disabled="disabled"
        @keydown="handleKeydown"
      />
      <Button
        type="submit"
        size="icon"
        class="h-10 w-10 sm:h-11 sm:w-11 shrink-0 transition-all duration-200"
        :disabled="isDisabled"
      >
        <Send class="w-4 h-4 sm:w-5 sm:h-5" />
        <span class="sr-only">Enviar mensaje</span>
      </Button>
    </form>
  </div>
</template>
