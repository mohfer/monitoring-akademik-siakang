<template>
    <PinInput v-if="!isAuthenticated" @authenticated="onAuthenticated" />
    <div v-else class="h-screen flex bg-background text-foreground overflow-hidden">

        <!-- Mobile Sidebar Overlay -->
        <div v-if="sidebarOpen" @click="sidebarOpen = false"
            class="fixed inset-0 bg-black/50 z-40 lg:hidden"></div>

        <!-- Sidebar -->
        <aside :class="[
            'fixed lg:static inset-y-0 left-0 z-50 w-64 border-r border-border flex flex-col bg-background shrink-0 transition-transform duration-200',
            sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
        ]">
            <!-- Logo -->
            <div class="h-14 flex items-center justify-between px-5 border-b border-border">
                <div class="flex items-center gap-2.5">
                    <div class="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
                        <LayoutDashboard :size="14" class="text-primary-foreground" />
                    </div>
                    <span class="font-semibold text-sm tracking-tight">Siakang Monitor</span>
                </div>
                <button @click="sidebarOpen = false" class="lg:hidden p-1 text-muted-foreground hover:text-foreground">
                    <X :size="18" />
                </button>
            </div>

            <!-- Navigation -->
            <nav class="flex-1 p-3 space-y-0.5 overflow-y-auto">
                <button v-for="tab in tabs" :key="tab.id" @click="activeTab = tab.id; sidebarOpen = false" :class="[
                    'w-full flex items-center gap-2.5 px-3 py-2 text-sm rounded-md transition-colors',
                    activeTab === tab.id
                        ? 'bg-accent text-accent-foreground font-medium'
                        : 'text-muted-foreground hover:bg-accent/50 hover:text-foreground'
                ]">
                    <component :is="tab.icon" :size="16" />
                    <span>{{ tab.label }}</span>
                    <span v-if="tab.count !== undefined"
                        class="ml-auto text-xs text-muted-foreground font-mono">{{ tab.count }}</span>
                </button>
            </nav>

            <!-- Footer -->
            <div class="p-3 border-t border-border">
                <Button @click="openModal(); sidebarOpen = false" class="w-full">
                    <Plus :size="16" class="mr-2" />
                    <span>New Task</span>
                </Button>
                <div class="flex items-center justify-between mt-3 px-1">
                    <span class="text-xs text-muted-foreground">v1.0.0</span>
                    <div class="flex items-center gap-1">
                        <Button variant="ghost" size="icon" @click="toggleDark" class="h-8 w-8">
                            <Sun v-if="isDark" :size="16" />
                            <Moon v-else :size="16" />
                        </Button>
                        <Button variant="ghost" size="icon" @click="handleLogout" class="h-8 w-8" title="Logout">
                            <Lock :size="16" />
                        </Button>
                    </div>
                </div>
            </div>
        </aside>

        <!-- Main Content -->
        <main class="flex-1 flex flex-col overflow-hidden min-w-0">
            <!-- Header -->
            <header class="h-14 flex items-center justify-between px-4 sm:px-6 border-b border-border shrink-0">
                <div class="flex items-center gap-3">
                    <Button variant="ghost" size="icon" @click="sidebarOpen = true" class="lg:hidden h-9 w-9 -ml-2">
                        <Menu :size="18" />
                    </Button>
                    <div>
                        <h1 class="text-sm font-semibold">{{ currentTabLabel }}</h1>
                        <p class="text-xs text-muted-foreground">{{ filteredTasks.length }} tasks</p>
                    </div>
                </div>
                <div class="flex items-center gap-2">
                    <Button @click="openModal()" class="lg:hidden" size="icon">
                        <Plus :size="16" />
                    </Button>
                    <Button variant="ghost" size="icon" @click="fetchTasks" class="h-9 w-9">
                        <RefreshCw :size="16" />
                    </Button>
                </div>
            </header>

            <!-- Content Area -->
            <div class="flex-1 overflow-auto p-4 sm:p-6">
                <draggable v-model="filteredTasks" item-key="id"
                    class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4" @start="isDragging = true"
                    @end="onDragEnd" handle=".drag-handle" :animation="200" :force-fallback="true"
                    :gpu-acceleration="false" ghost-class="opacity-0" fallback-class="rub-float-effect">
                    <template #item="{ element }">
                        <TaskCard :task="element" @edit="openModal(element)" @delete="deleteTask(element.id)"
                            @refresh="fetchTasks" @clone="cloneTask(element)" />
                    </template>
                </draggable>

                <!-- Empty State -->
                <div v-if="filteredTasks.length === 0"
                    class="flex flex-col items-center justify-center py-16 sm:py-20 text-center">
                    <div class="w-12 h-12 rounded-lg bg-muted flex items-center justify-center mb-4">
                        <LayoutDashboard :size="24" class="text-muted-foreground" />
                    </div>
                    <h3 class="text-sm font-medium mb-1">No tasks</h3>
                    <p class="text-sm text-muted-foreground mb-4">Get started by creating a new task.</p>
                    <Button variant="link" @click="openModal()" class="gap-1">
                        <Plus :size="14" /> Create task
                    </Button>
                </div>
            </div>
        </main>

        <TaskModal v-if="showModal" :task="selectedTask" @close="closeModal" @save="saveTask" />
    </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import axios from 'axios'
import draggable from 'vuedraggable'
import TaskCard from './components/TaskCard.vue'
import TaskModal from './components/TaskModal.vue'
import PinInput from './components/PinInput.vue'
import Button from './components/ui/Button.vue'
import { Moon, Sun, Plus, LayoutDashboard, LayoutGrid, GraduationCap, CreditCard, RefreshCw, Menu, X, Lock } from 'lucide-vue-next'

const isAuthenticated = ref(false)
const tasks = ref([])
const showModal = ref(false)
const selectedTask = ref(null)
const isDark = ref(false)
const isDragging = ref(false)
const activeTab = ref('all')
const sidebarOpen = ref(false)

const API_URL = '/api'

const tabs = computed(() => [
    { id: 'all', label: 'All Tasks', icon: LayoutGrid, count: tasks.value.length },
    { id: 'nilai', label: 'Monitor Nilai', icon: GraduationCap, count: tasks.value.filter(t => (t.monitor_type || 'nilai') === 'nilai').length },
    { id: 'krs', label: 'Monitor KRS', icon: CreditCard, count: tasks.value.filter(t => t.monitor_type === 'krs').length }
])

const currentTabLabel = computed(() => {
    const tab = tabs.value.find(t => t.id === activeTab.value)
    return tab ? tab.label : 'All Tasks'
})

const filteredTasks = computed({
    get() {
        if (activeTab.value === 'all') return tasks.value
        return tasks.value.filter(t => {
            const type = t.monitor_type || 'nilai'
            return type === activeTab.value
        })
    },
    set(value) {
        if (activeTab.value === 'all') {
            tasks.value = value
        } else {
            const newFullList = [...tasks.value]
            const indicesToUpdate = []
            newFullList.forEach((t, index) => {
                const type = t.monitor_type || 'nilai'
                if (type === activeTab.value) {
                    indicesToUpdate.push(index)
                }
            })
            indicesToUpdate.forEach((originalIndex, i) => {
                newFullList[originalIndex] = value[i]
            })
            tasks.value = newFullList
        }
    }
})

const toggleDark = () => {
    isDark.value = !isDark.value
    if (isDark.value) {
        document.documentElement.classList.add('dark')
        localStorage.setItem('theme', 'dark')
    } else {
        document.documentElement.classList.remove('dark')
        localStorage.setItem('theme', 'light')
    }
}

const onDragEnd = async () => {
    isDragging.value = false
    const orderedIds = tasks.value.map(t => t.id)
    try {
        await axios.put(`${API_URL}/tasks/reorder`, orderedIds)
    } catch (e) {
        console.error("Failed to reorder", e)
    }
}

const handleLogout = () => {
    localStorage.removeItem('siakang_pin_verified')
    isAuthenticated.value = false
}

const onAuthenticated = () => {
    isAuthenticated.value = true
    fetchTasks()
}

const cloneTask = async (task) => {
    const newTask = {
        name: `${task.name} (Copy)`,
        login_id: task.login_id,
        password: task.password,
        chat_id: task.chat_id,
        whatsapp_number: task.whatsapp_number,
        target_semester_code: task.target_semester_code,
        monitor_type: task.monitor_type,
        target_courses: task.target_courses,
        interval: task.interval
    }
    await saveTask(newTask)
}

const fetchTasks = async () => {
    if (isDragging.value) return
    try {
        const res = await axios.get(`${API_URL}/tasks`)
        tasks.value = res.data.data
    } catch (e) {
        console.error(e)
    }
}

const openModal = (task = null) => {
    selectedTask.value = task ? { ...task } : null
    showModal.value = true
}

const closeModal = () => {
    showModal.value = false
    selectedTask.value = null
}

const saveTask = async (taskData) => {
    try {
        if (taskData.id) {
            await axios.put(`${API_URL}/tasks/${taskData.id}`, taskData)
        } else {
            await axios.post(`${API_URL}/tasks`, taskData)
        }
        fetchTasks()
        closeModal()
    } catch (e) {
        console.error(e)
        alert('Error saving task')
    }
}

const deleteTask = async (id) => {
    if (!confirm('Are you sure you want to delete this task?')) return
    try {
        await axios.delete(`${API_URL}/tasks/${id}`)
        fetchTasks()
    } catch (e) {
        console.error(e)
        alert('Error deleting task')
    }
}

onMounted(() => {
    if (localStorage.getItem('siakang_pin_verified') === 'true') {
        isAuthenticated.value = true
        fetchTasks()
        setInterval(fetchTasks, 30000)
    }

    const savedTheme = localStorage.getItem('theme')
    if (savedTheme === 'dark') {
        isDark.value = true
        document.documentElement.classList.add('dark')
    } else if (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches) {
        isDark.value = true
        document.documentElement.classList.add('dark')
    }
})
</script>
