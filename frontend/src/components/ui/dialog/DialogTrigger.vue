<script setup>
import { DialogTrigger } from 'reka-ui'

const props = defineProps({
  asChild: { type: Boolean, required: false }
})
</script>

<template>
  <DialogTrigger :as-child="props.asChild">
    <slot />
  </DialogTrigger>
</template>
