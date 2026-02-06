<script setup>
import { ref } from 'vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import DocumentView from './components/documents/DocumentView.vue'
import SearchView from './components/search/SearchView.vue'
import ChatView from './components/chat/ChatView.vue'
import OriginsView from './components/origins/OriginsView.vue'
import ClassifyView from './components/classify/ClassifyView.vue'

const activeView = ref('search')
</script>

<template>
  <div class="h-screen flex flex-col md:flex-row bg-zinc-100">
    <AppSidebar 
      :active-view="activeView" 
      @update:active-view="activeView = $event" 
    />
    <main class="flex-1 overflow-hidden">
      <Transition name="fade" mode="out-in">
        <DocumentView v-if="activeView === 'documents'" />
        <SearchView v-else-if="activeView === 'search'" />
        <OriginsView v-else-if="activeView === 'origins'" />
        <ClassifyView v-else-if="activeView === 'classify'" />
        <ChatView v-else-if="activeView === 'chat'" />
      </Transition>
    </main>
  </div>
</template>
