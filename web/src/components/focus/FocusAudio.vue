<template>
  <div class="focus-audio">
    <div v-if="selected" class="focus-audio-mini" aria-label="当前专注音频">
      <button class="audio-mini-name" title="选择专注音频" @click="open">
        <img :src="selected.cover" alt="" /><span>{{ selected.name }}</span><PlannerIcon name="right" />
      </button>
      <button class="icon-button" :aria-label="playing || buffering ? '暂停背景音' : '播放背景音'" :title="playing || buffering ? '暂停背景音' : '播放背景音'" @click="toggle">
        <PlannerIcon :name="playing || buffering ? 'pause' : 'play'" />
      </button>
    </div>
    <p v-if="error && !opened" class="audio-inline-error" role="alert">{{ error }}<button class="text-button" @click="open">查看音频</button></p>
    <audio ref="player" class="focus-background-audio" preload="metadata" :loop="preferences.loop"
      @playing="syncPlayback" @pause="syncPlayback" @ended="syncPlayback" @waiting="buffering = true"
      @timeupdate="syncTime" @loadedmetadata="syncTime" @durationchange="syncTime" @error="playbackError"></audio>
    <PlannerDialog :open="opened" title="专注音频" class="focus-audio-dialog" @close="close">
      <div class="audio-library-body">
        <div class="audio-library-toolbar">
          <div class="audio-library-tabs" role="group" aria-label="音频分类">
            <button :class="{ selected: category === 'ambient' }" :aria-pressed="category === 'ambient'" @click="category = 'ambient'">环境音</button>
            <button :class="{ selected: category === 'local' }" :aria-pressed="category === 'local'" @click="category = 'local'">本地音频 <span>{{ localTracks.length }}</span></button>
          </div>
          <button class="outline-button audio-upload" :disabled="uploading || libraryLoading" @click="fileInput?.click()">
            <PlannerIcon :name="uploading ? 'clock' : 'upload'" /><span>{{ uploading ? '正在导入' : '上传音频' }}</span>
          </button>
          <input ref="fileInput" class="audio-file-input" type="file" accept="audio/*,.mp3,.wav,.m4a,.aac,.ogg,.oga,.opus,.flac,.weba,.webm" multiple aria-label="上传本地音频" @change="upload" />
        </div>
        <div v-if="error || libraryError" class="audio-message error" role="alert">
          <span>{{ error || libraryError }}</span><button v-if="libraryError" class="text-button" @click="loadLibrary">重试</button>
          <button v-else class="icon-button" aria-label="关闭音频提示" @click="error = ''"><PlannerIcon name="close" /></button>
        </div>
        <p v-if="notice" class="audio-message" role="status">{{ notice }}</p>
        <p v-if="uploading" class="audio-message" role="status">{{ uploadCaption }}</p>
        <div v-if="category === 'ambient'" class="audio-tile-grid">
          <button v-for="track in builtInTracks" :key="track.id" class="audio-tile" :class="{ chosen: selected?.id === track.id }"
            :aria-label="`播放${track.name}`" :aria-pressed="selected?.id === track.id" @click="choose(track)">
            <span class="audio-cover"><img :src="track.cover" alt="" width="240" height="288" /><span class="audio-tile-state"><PlannerIcon :name="selected?.id === track.id && playing ? 'sound' : selected?.id === track.id ? 'check' : 'play'" /></span></span>
            <strong>{{ track.name }}</strong>
          </button>
        </div>
        <template v-else>
          <div v-if="libraryLoading" class="audio-empty" role="status">正在读取本地音频</div>
          <div v-else-if="!localTracks.length" class="audio-empty">
            <span class="audio-empty-symbol"><PlannerIcon name="music" /></span><h3>还没有本地音频</h3>
            <button class="outline-button" :disabled="uploading" @click="fileInput?.click()"><PlannerIcon name="upload" />选择音频</button>
          </div>
          <div v-else class="audio-local-list">
            <div v-for="track in localTracks" :key="track.id" class="audio-local-row" :class="{ chosen: selected?.id === track.id }">
              <button class="audio-local-select" :aria-label="`播放${track.name}`" :aria-pressed="selected?.id === track.id" @click="choose(track)">
                <span class="audio-local-icon"><PlannerIcon :name="selected?.id === track.id && playing ? 'sound' : 'music'" /></span>
                <span><strong>{{ track.name }}</strong><small>{{ audioTime(track.duration || 0) }} · {{ ((track.size || 0) / 1048576).toFixed(1) }} MB</small></span>
                <PlannerIcon :name="selected?.id === track.id ? 'check' : 'play'" />
              </button>
              <button class="icon-button" :aria-label="`删除${track.name}`" title="删除音频" :disabled="uploading || deleting" @click="deleteTarget = track"><PlannerIcon name="delete" /></button>
            </div>
          </div>
        </template>
        <div v-if="deleteTarget" class="audio-delete-confirm" role="group" aria-label="删除音频确认">
          <p>删除“{{ deleteTarget.name }}”？</p><span>原始文件不受影响。</span>
          <div><button class="outline-button" :disabled="deleting" @click="deleteTarget = null">取消</button><button class="danger-button" :disabled="deleting" @click="removeTrack">{{ deleting ? '正在删除' : '删除音频' }}</button></div>
        </div>
      </div>
      <footer class="audio-player" aria-label="音频播放控制">
        <div class="audio-now-playing">
          <img v-if="selected" :src="selected.cover" alt="" width="48" height="48" />
          <span v-else class="audio-player-placeholder"><PlannerIcon name="music" /></span>
          <div class="audio-track-caption"><strong>{{ selected?.name || '未选择音频' }}</strong><span>{{ buffering ? '正在缓冲' : playing ? '正在播放' : selected ? '已暂停' : '专注音频' }}</span></div>
          <button class="audio-play-button" :disabled="!selected" :aria-label="playing || buffering ? '暂停音频' : '播放音频'" :title="playing || buffering ? '暂停音频' : '播放音频'" @click="toggle"><PlannerIcon :name="playing || buffering ? 'pause' : 'play'" /></button>
          <button class="icon-button" :disabled="!selected" aria-label="关闭背景音" title="关闭背景音" @click="powerOff"><PlannerIcon name="power" /></button>
        </div>
        <div class="audio-seek"><time>{{ audioTime(position) }}</time><input type="range" min="0" :max="Math.max(length, 1)" step=".1" :value="position" :disabled="!selected || !length" aria-label="音频播放进度" @input="seek" /><time>{{ audioTime(length) }}</time></div>
        <div class="audio-volume-row">
          <button class="icon-button" :aria-label="preferences.muted ? '取消静音' : '静音'" :title="preferences.muted ? '取消静音' : '静音'" :aria-pressed="preferences.muted" @click="preferences.muted = !preferences.muted"><PlannerIcon :name="preferences.muted || !preferences.volume ? 'mute' : 'sound'" /></button>
          <input v-model.number="preferences.volume" type="range" min="0" max="1" step=".01" aria-label="背景音量" />
          <output>{{ Math.round(preferences.volume * 100) }}%</output>
          <button class="audio-loop-button" :class="{ selected: preferences.loop }" :aria-pressed="preferences.loop" :title="preferences.loop ? '单曲循环' : '播放一次'" aria-label="单曲循环" @click="preferences.loop = !preferences.loop"><PlannerIcon name="repeat" /><span>{{ preferences.loop ? '单曲循环' : '播放一次' }}</span></button>
        </div>
      </footer>
    </PlannerDialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import PlannerDialog from '@/components/planner/PlannerDialog.vue'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import { AUDIO_PREFERENCES_KEY, audioFingerprint, audioTime, builtInTracks, deleteLocalTrack, inspectAudio,
  loadLocalTracks, MAX_TRACKS, parseAudioPreferences, saveLocalTrack, type FocusTrack } from './audio'

const props = defineProps<{ ducked?: boolean }>()
const emit = defineEmits<{ (event: 'playingChange', value: boolean): void }>()
let saved: string | null = null
try { saved = localStorage.getItem(AUDIO_PREFERENCES_KEY) } catch { /* Playback also works without preferences. */ }
const preferences = reactive(parseAudioPreferences(saved))
const player = ref<HTMLAudioElement>()
const fileInput = ref<HTMLInputElement>()
const opened = ref(false)
const category = ref<'ambient' | 'local'>('ambient')
const localTracks = ref<FocusTrack[]>([])
const selected = computed(() => [...builtInTracks, ...localTracks.value].find(track => track.id === preferences.selectedId))
const playing = ref(false)
const buffering = ref(false)
const position = ref(0)
const length = ref(0)
const error = ref('')
const notice = ref('')
const libraryError = ref('')
const libraryLoading = ref(true)
const uploading = ref(false)
const uploadCaption = ref('')
const deleting = ref(false)
const deleteTarget = ref<FocusTrack | null>(null)
let objectUrl = ''
let loadedId = ''
let playbackSequence = 0
let playTimeout: ReturnType<typeof setTimeout>
let disposed = false
function open() { opened.value = true }
function close() { opened.value = false; deleteTarget.value = null }
defineExpose({ open, close })
function syncPlayback() {
  playing.value = !!player.value && !player.value.paused && !player.value.ended
  buffering.value = false
}
function syncTime() {
  position.value = player.value?.currentTime || 0
  length.value = Number.isFinite(player.value?.duration) ? player.value!.duration : 0
}
function applyVolume() {
  if (player.value) {
    player.value.volume = preferences.volume * (props.ducked ? .2 : 1)
    player.value.muted = preferences.muted
  }
}
function pause() {
  ++playbackSequence
  clearTimeout(playTimeout)
  player.value?.pause()
  playing.value = false
  buffering.value = false
}
function releaseSource() {
  pause()
  player.value?.removeAttribute('src')
  player.value?.load()
  if (objectUrl) URL.revokeObjectURL(objectUrl)
  objectUrl = ''
  loadedId = ''
  position.value = length.value = 0
}
function setSource(track: FocusTrack) {
  if (!player.value || loadedId === track.id) return
  releaseSource()
  const source = track.source || (track.file ? (objectUrl = URL.createObjectURL(track.file)) : '')
  if (!source) return
  player.value.src = source
  player.value.loop = preferences.loop
  loadedId = track.id
  applyVolume()
  player.value.load()
}
async function play() {
  if (!player.value || !selected.value) return
  setSource(selected.value)
  error.value = ''
  const sequence = ++playbackSequence
  buffering.value = true
  clearTimeout(playTimeout)
  playTimeout = setTimeout(() => {
    if (sequence !== playbackSequence || disposed) return
    pause()
    error.value = '音频加载超时，请重新播放或选择其他音频。'
  }, 15000)
  try {
    await player.value.play()
    if (sequence === playbackSequence && !disposed) { clearTimeout(playTimeout); syncPlayback() }
  } catch (reason) {
    if (sequence !== playbackSequence || disposed) return
    clearTimeout(playTimeout)
    buffering.value = playing.value = false
    error.value = reason instanceof DOMException && reason.name === 'NotAllowedError'
      ? '浏览器暂未允许播放，请点击播放按钮重试。' : '无法播放此音频，请检查文件或选择其他音频。'
  }
}
function choose(track: FocusTrack) {
  preferences.selectedId = track.id
  notice.value = ''
  void play()
}
function toggle() { if (playing.value || buffering.value) pause(); else void play() }
function powerOff() { releaseSource(); preferences.selectedId = ''; error.value = '' }
function playbackError() {
  if (!player.value?.error || !loadedId || disposed) return
  pause()
  error.value = '音频加载失败，请重试或选择其他音频。'
}
function seek(event: Event) {
  if (!player.value || !length.value) return
  player.value.currentTime = Math.min(length.value, Math.max(0, Number((event.target as HTMLInputElement).value)))
  syncTime()
}
async function loadLibrary() {
  libraryLoading.value = true
  libraryError.value = ''
  try {
    const tracks = await loadLocalTracks()
    if (disposed) return
    localTracks.value = tracks
    if (selected.value) setSource(selected.value)
    else if (preferences.selectedId.startsWith('local:')) preferences.selectedId = ''
  } catch (reason) {
    if (!disposed) libraryError.value = reason instanceof Error ? reason.message : '本地音频读取失败。'
  } finally { if (!disposed) libraryLoading.value = false }
}
async function upload(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length || uploading.value) return
  category.value = 'local'
  error.value = notice.value = ''
  if (files.length + localTracks.value.length > MAX_TRACKS) {
    error.value = '最多保存 20 首本地音频，请减少选择或删除部分音频。'; return
  }
  uploading.value = true
  let count = 0
  const failures: string[] = []
  try {
    for (const file of files) {
      if (disposed) break
      uploadCaption.value = `正在导入 ${count + failures.length + 1}/${files.length}：${file.name}`
      try {
        const duration = await inspectAudio(file)
        if (disposed) break
        const track: FocusTrack = { id: `local:${crypto.randomUUID()}`, name: file.name.replace(/\.[^.]+$/, '').slice(0, 160),
          cover: '/focus-audio/quiet.png', file, duration, size: file.size, fingerprint: audioFingerprint(file), createdAt: Date.now() }
        await saveLocalTrack(track)
        if (disposed) break
        localTracks.value.unshift(track)
        count++
      } catch (reason) { failures.push(`${file.name}：${reason instanceof Error ? reason.message : '导入失败。'}`) }
    }
    if (count) { notice.value = `已保存 ${count} 首本地音频`; libraryError.value = '' }
    if (failures.length) error.value = failures.join('；')
  } finally { uploading.value = false; uploadCaption.value = '' }
}
async function removeTrack() {
  const track = deleteTarget.value
  if (!track || deleting.value) return
  deleting.value = true
  try {
    await deleteLocalTrack(track.id)
    if (disposed) return
    if (preferences.selectedId === track.id) powerOff()
    localTracks.value = localTracks.value.filter(item => item.id !== track.id)
    deleteTarget.value = null
    notice.value = '音频已从本地音频库移除'
  } catch (reason) { error.value = reason instanceof Error ? reason.message : '删除失败，请重试。' }
  finally { deleting.value = false }
}
watch(playing, value => emit('playingChange', value))
watch(preferences, () => {
  applyVolume()
  try { localStorage.setItem(AUDIO_PREFERENCES_KEY, JSON.stringify(preferences)) } catch { /* Local files use IndexedDB. */ }
})
watch(() => props.ducked, applyVolume)
onMounted(() => { if (selected.value) setSource(selected.value); void loadLibrary() })
onBeforeUnmount(() => { disposed = true; releaseSource(); emit('playingChange', false) })
</script>

<style src="./audio.css"></style>
