<template>
  <main class="connection-screen">
    <aside class="desktop-rail connection-rail" aria-label="主导航">
      <router-link to="/index" class="rail-brand" aria-label="SmartTodo 首页"><PlannerIcon name="tasks" /></router-link>
      <router-link class="rail-item" to="/index"><PlannerIcon name="calendar" /><span>计划</span></router-link>
      <router-link class="rail-item" to="/index?view=schedule"><PlannerIcon name="grid" /><span>视图</span></router-link>
      <router-link class="rail-item" to="/tomato"><PlannerIcon name="clock" /><span>专注</span></router-link>
      <router-link class="rail-item selected" to="/connect" aria-current="page"><PlannerIcon name="chat" /><span>关联</span></router-link>
      <router-link class="rail-item rail-tools" to="/tools"><PlannerIcon name="settings" /><span>工具箱</span></router-link>
    </aside>
    <div class="connection-content">
      <header class="connection-topbar">
        <router-link to="/index" class="connection-brand">SmartTodo<span>.</span></router-link>
        <router-link to="/index" class="connection-back"><PlannerIcon name="back" />返回计划</router-link>
      </header>

      <section class="connection-heading">
        <div>
          <p class="connection-eyebrow">一起安排，也各自掌握</p>
          <h1>待办关联</h1>
        </div>
        <button v-if="!auth.localMode" class="connection-add-button" @click="inviteOpen = true">
          <PlannerIcon name="user-plus" />添加联系人
        </button>
      </section>

      <div v-if="auth.localMode" class="connection-unavailable">
        <PlannerIcon name="lock" />
        <div><h2>待办关联需要账号模式</h2><p>本地模式下，联系人与聊天功能不可用。</p></div>
        <router-link to="/tools">返回工具箱</router-link>
      </div>

      <div v-else-if="pageError" class="connection-alert" role="alert">{{ pageError }}</div>

      <section v-else class="connection-workspace" :class="[`pane-${mobilePane}`, { 'has-contact': !!activeContact }]">
        <aside class="connection-contacts" aria-label="联系人">
          <div class="connection-list-heading">
            <h2>联系人</h2><span>{{ contacts.length }}</span>
            <button class="icon-button" aria-label="添加联系人" title="添加联系人" @click="inviteOpen = true"><PlannerIcon name="user-plus" /></button>
          </div>

          <div class="connection-search">
            <PlannerIcon name="search" />
            <input v-model="search" aria-label="查找联系人" placeholder="搜索联系人" />
          </div>

          <div v-if="incoming.length" class="connection-invitations">
            <h3>新的邀请 <span>{{ incoming.length }}</span></h3>
            <article v-for="request in incoming" :key="request.id" class="connection-request">
              <span class="connection-avatar">{{ avatarLetter(request.displayName) }}</span>
              <div><strong>{{ request.displayName }}</strong><small>@{{ request.username }}</small></div>
              <button class="connection-accept" :aria-label="`接受 ${request.displayName} 的邀请`" @click="respond(request.id, 'accept')"><PlannerIcon name="check" /></button>
              <button class="connection-reject" :aria-label="`拒绝 ${request.displayName} 的邀请`" @click="respond(request.id, 'reject')"><PlannerIcon name="close" /></button>
            </article>
          </div>

          <div class="connection-contact-list" role="list">
            <button v-for="contact in filteredContacts" :key="contact.id" class="connection-contact"
              :class="{ selected: contact.id === activeId }" role="listitem" @click="selectContact(contact)">
              <span class="connection-avatar" :class="{ 'avatar-active': contact.unread }">{{ avatarLetter(contact.displayName) }}</span>
              <span class="connection-contact-copy">
                <span class="connection-contact-title"><strong>{{ contact.displayName }}</strong><time>{{ timeLabel(contact.updatedAt) }}</time></span>
                <span class="connection-contact-preview">{{ contact.lastMessage ? previewText(contact.lastMessage) : `@${contact.username}` }}</span>
              </span>
              <span v-if="contact.unread" class="connection-unread" :aria-label="`${contact.unread} 条未读消息`">{{ contact.unread > 99 ? '99+' : contact.unread }}</span>
            </button>
            <div v-if="!filteredContacts.length" class="connection-list-empty">
              <PlannerIcon name="chat" /><span>{{ contacts.length ? '没有匹配的联系人' : '还没有联系人' }}</span>
            </div>
          </div>

          <div v-if="outgoing.length" class="connection-outgoing">
            <h3>等待确认</h3>
            <div v-for="request in outgoing" :key="request.id" class="connection-outgoing-row">
              <span class="connection-avatar">{{ avatarLetter(request.displayName) }}</span>
              <span><strong>{{ request.displayName }}</strong><small>@{{ request.username }}</small></span>
              <span class="connection-pending">待确认</span>
            </div>
          </div>
        </aside>

        <section v-if="activeContact" class="connection-chat" aria-label="聊天">
          <header class="connection-chat-heading">
            <button class="connection-mobile-back" aria-label="返回联系人" @click="mobilePane = 'contacts'"><PlannerIcon name="back" /></button>
            <span class="connection-avatar">{{ avatarLetter(activeContact.displayName) }}</span>
            <div class="connection-chat-person">
              <h2>{{ activeContact.displayName }}</h2><span>@{{ activeContact.username }}</span>
            </div>
            <button v-if="activeContact.peerSharesToday" class="connection-plan-toggle" @click="mobilePane = 'plan'">
              <PlannerIcon name="calendar" />今日计划
            </button>
            <button class="icon-button connection-menu" aria-label="关联设置" title="关联设置" @click="settingsOpen = !settingsOpen"><PlannerIcon name="more" /></button>
          </header>

          <div v-if="settingsOpen" class="connection-settings">
            <label class="connection-share-setting">
              <span><strong>允许查看我的今日计划</strong><small>今日任务、时间及完成状态，不含备注</small></span>
              <input type="checkbox" :checked="activeContact.sharesToday" :disabled="shareBusy" @change="setSharing(($event.target as HTMLInputElement).checked)" />
            </label>
            <button class="connection-remove" @click="removeConfirm = !removeConfirm">移除联系人并清空聊天</button>
            <div v-if="removeConfirm" class="connection-remove-confirm">
              <span>聊天记录会一并删除，共享权限也会关闭。</span>
              <button @click="removeContact">确认移除</button>
            </div>
          </div>

          <div ref="messageViewport" class="connection-messages" aria-live="polite" aria-relevant="additions">
            <button v-if="hasOlder" class="connection-load-older" :disabled="historyBusy" @click="loadOlder">
              {{ historyBusy ? '正在读取' : '查看更早消息' }}
            </button>
            <div v-if="!messages.length" class="connection-chat-empty">
              <img src="/planner/focus.png" alt="" />
              <strong>从一句问候开始</strong><span>也可以把今天的计划分享给对方。</span>
            </div>
            <article v-for="message in messages" :key="message.id" class="connection-message"
              :class="{ mine: message.sender === auth.user?.username, 'message-revoked': message.revoked }">
              <span v-if="message.sender !== auth.user?.username" class="connection-avatar message-avatar">{{ avatarLetter(activeContact.displayName) }}</span>
              <div class="connection-bubble-wrap">
                <button v-if="message.kind === 'plan' && message.plan && !message.revoked"
                  class="connection-plan-message" @click="openSnapshot(message)">
                  <span class="shared-plan-icon"><PlannerIcon name="calendar" /></span>
                  <span class="shared-plan-copy"><strong>{{ message.plan.title }}</strong><small>{{ message.plan.day }} · {{ message.plan.doneCount }}/{{ message.plan.taskCount }} 项完成</small></span>
                  <PlannerIcon name="right" />
                </button>
                <p v-else class="connection-bubble">{{ message.revoked ? '计划分享已撤回' : message.body }}</p>
                <div class="connection-message-meta">
                  <time>{{ timeLabel(message.createdAt) }}</time>
                  <button v-if="message.kind === 'plan' && message.canRevoke && !message.revoked" class="connection-revoke" @click="revokePlan(message.id)">撤回分享</button>
                </div>
              </div>
            </article>
            <div ref="messageEnd"></div>
          </div>

          <p v-if="sendError" class="connection-send-error" role="alert">{{ sendError }}</p>
          <form class="connection-composer" @submit.prevent="sendMessage">
            <textarea v-model="draft" aria-label="输入消息" rows="1" maxlength="2000" placeholder="发送消息…"
              @keydown.enter.exact="sendOnEnter"></textarea>
            <button type="button" class="connection-share-button" aria-label="分享今日计划" title="分享今日计划"
              :disabled="sendBusy" @click="openShare"><PlannerIcon name="calendar" /></button>
            <button type="submit" class="connection-send-button" aria-label="发送消息" :disabled="sendBusy || !draft.trim()"><PlannerIcon name="send" /></button>
          </form>
        </section>

        <section v-if="activeContact && mobilePane === 'plan'" class="connection-plan connection-mobile-plan" aria-label="对方今日计划">
          <header class="connection-mobile-plan-heading">
            <button class="connection-mobile-back" aria-label="返回聊天" @click="mobilePane = 'chat'"><PlannerIcon name="back" /></button>
            <div><h2>{{ activeContact.displayName }}的今日计划</h2><span>{{ todayCaption }}</span></div>
          </header>
          <template v-if="activeContact.peerSharesToday">
            <p v-if="livePlanError" class="connection-plan-error" role="alert">{{ livePlanError }}</p>
            <PlanSections v-else-if="livePlan" :plan="livePlan" :owner="activeContact.displayName" />
            <div v-else class="connection-plan-loading"><span class="loading-line"></span>正在读取今日计划</div>
          </template>
          <div v-else class="connection-plan-private"><PlannerIcon name="lock" /><span>对方已关闭今日计划共享</span></div>
        </section>

        <section v-if="!activeContact" class="connection-chat connection-chat-placeholder">
          <div><PlannerIcon name="chat" /><h2>选择一位联系人</h2><span>聊天和共享的计划仅对你们双方可见。</span></div>
        </section>

        <aside v-if="activeContact" class="connection-plan" aria-label="对方今日计划">
          <header class="connection-plan-heading">
            <div><p>共享计划</p><h2>{{ activeContact.displayName }}</h2><span>{{ todayCaption }}</span></div>
            <PlannerIcon name="calendar" />
          </header>
          <div v-if="activeContact.peerSharesToday">
            <p v-if="livePlanError" class="connection-plan-error" role="alert">{{ livePlanError }}</p>
            <PlanSections v-else-if="livePlan" :plan="livePlan" :owner="activeContact.displayName" />
            <div v-else class="connection-plan-loading"><span class="loading-line"></span>正在读取今日计划</div>
          </div>
          <div v-else class="connection-plan-private"><PlannerIcon name="lock" /><span>对方尚未开放今日计划</span></div>
          <div class="connection-sharing-control">
            <label class="connection-share-setting">
              <span><strong>共享我的今日计划</strong><small>仅 {{ activeContact.displayName }} 可见，不含备注</small></span>
              <input type="checkbox" :checked="activeContact.sharesToday" :disabled="shareBusy" @change="setSharing(($event.target as HTMLInputElement).checked)" />
            </label>
          </div>
        </aside>
      </section>

      <footer v-if="!auth.localMode && !pageError" class="connection-footer">
        <PlannerIcon name="lock" /><span>计划仅在你选择分享后对联系人可见</span>
      </footer>
    </div>

    <nav v-if="!auth.localMode" class="connection-mobile-nav" aria-label="主导航">
      <router-link to="/index"><PlannerIcon name="calendar" /><span>计划</span></router-link>
      <router-link to="/index?view=schedule"><PlannerIcon name="grid" /><span>视图</span></router-link>
      <router-link to="/tomato"><PlannerIcon name="clock" /><span>专注</span></router-link>
      <router-link to="/connect" class="selected" aria-current="page"><PlannerIcon name="chat" /><span>关联</span></router-link>
      <router-link to="/tools"><PlannerIcon name="settings" /><span>工具箱</span></router-link>
    </nav>

    <PlannerDialog :open="inviteOpen" title="添加联系人" @close="inviteOpen = false">
      <form class="connection-dialog-form" @submit.prevent="invite">
        <label>对方账号<input v-model="inviteUsername" autofocus required maxlength="15" autocomplete="off" placeholder="输入对方的账号" /></label>
        <p class="connection-dialog-note">发送邀请后，对方接受才能开始聊天。</p>
        <p v-if="dialogError" class="connection-alert" role="alert">{{ dialogError }}</p>
        <div class="connection-dialog-actions"><button type="button" class="account-secondary" @click="inviteOpen = false">取消</button><button class="account-primary" :disabled="inviteBusy"><PlannerIcon name="user-plus" />发送邀请</button></div>
      </form>
    </PlannerDialog>

    <PlannerDialog :open="shareOpen" title="分享今日计划" :busy="shareBusy" @close="shareOpen = false">
      <div class="connection-dialog-form">
        <p class="connection-dialog-note">{{ activeContact?.displayName }}会收到今天的计划快照，不包含未来日期。</p>
        <label class="connection-include-notes"><input v-model="includeNotes" type="checkbox" /><span>同时分享任务备注</span></label>
        <div v-if="sharePreview" class="connection-share-preview">
          <strong>{{ sharePreview.title }}</strong><span>{{ sharePreview.sections.reduce((sum, section) => sum + section.tasks.length, 0) }} 项今日安排</span>
          <p v-for="section in sharePreview.sections.filter(item => item.tasks.length)" :key="section.id">{{ section.title }} · {{ section.tasks.length }} 项</p>
        </div>
        <p v-if="dialogError" class="connection-alert" role="alert">{{ dialogError }}</p>
        <div class="connection-dialog-actions"><button type="button" class="account-secondary" @click="shareOpen = false">取消</button><button class="account-primary" :disabled="shareBusy || !sharePreview" @click="shareToday"><PlannerIcon name="send" />分享计划</button></div>
      </div>
    </PlannerDialog>

    <PlannerDialog :open="!!snapshotView" :title="snapshotView?.title || '今日计划'" @close="snapshotView = null">
      <div v-if="snapshotView" class="connection-snapshot-heading">{{ snapshotView.day }} · {{ snapshotView.doneCount }}/{{ snapshotView.taskCount }} 项完成</div>
      <PlanSections v-if="snapshotView" :plan="snapshotView" :owner="activeContact?.displayName || ''" />
      <p v-if="snapshotView && !snapshotView.includesNotes" class="connection-dialog-note">分享时未包含任务备注。</p>
    </PlannerDialog>
  </main>
</template>

<script setup lang="ts">
import { computed, defineComponent, h, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import PlannerDialog from '@/components/planner/PlannerDialog.vue'
import PlannerIcon from '@/components/planner/PlannerIcon.vue'
import { auth } from '@/auth'
import { apiFetch } from '@/http'

interface SharedTask {
  id: string
  title: string
  notes?: string
  kind: 'task' | 'event'
  time?: string
  endTime?: string
  done: boolean
}
interface PlanSection { id: string; title: string; color: string; tasks: SharedTask[] }
interface SharedPlan { day: string; title: string; sections: PlanSection[]; taskCount?: number; doneCount?: number; includesNotes?: boolean }
interface ChatMessage {
  id: number
  sender: string
  kind: 'text' | 'plan'
  body: string
  revoked: boolean
  createdAt: string
  clientId: string
  plan?: SharedPlan
  canRevoke?: boolean
}
interface Contact {
  id: number
  username: string
  displayName: string
  sharesToday: boolean
  peerSharesToday: boolean
  unread: number
  lastMessage: ChatMessage | null
  updatedAt: string
}
interface ContactRequest { id: number; username: string; displayName: string }
interface Overview { contacts: Contact[]; incoming: ContactRequest[]; outgoing: ContactRequest[] }
interface PlanReply { title: string; sections: PlanSection[] }

const PlanSections = defineComponent({
  props: { plan: { type: Object as () => SharedPlan, required: true }, owner: { type: String, required: true } },
  setup(props) {
    return () => h('div', { class: 'connection-plan-sections' }, [
      h('h3', props.plan.title),
      ...props.plan.sections.map(section => h('section', { class: `connection-plan-section color-${section.color}`, key: section.id }, [
        h('header', [h('span', section.title), h('small', `${section.tasks.filter(task => !task.done).length}`)]),
        ...(section.tasks.length ? section.tasks.map(task => h('article', { class: { 'shared-task-done': task.done }, key: task.id }, [
          h('span', { class: 'shared-task-check', 'aria-hidden': 'true' }, task.done ? '✓' : ''),
          h('div', [
            h('strong', task.title),
            task.time ? h('small', `${task.time}${task.endTime ? `–${task.endTime}` : ''}`) : null,
            task.notes ? h('p', task.notes) : null,
          ]),
        ])) : [h('p', { class: 'connection-plan-section-empty' }, '暂无事项')]),
      ])),
    ])
  },
})

const contacts = ref<Contact[]>([])
const incoming = ref<ContactRequest[]>([])
const outgoing = ref<ContactRequest[]>([])
const activeId = ref<number | null>(null)
const messages = ref<ChatMessage[]>([])
const livePlan = ref<SharedPlan | null>(null)
const sharePreview = ref<PlanReply | null>(null)
const snapshotView = ref<SharedPlan | null>(null)
const snapshotMessageId = ref<number | null>(null)
const mobilePane = ref<'contacts' | 'chat' | 'plan'>('contacts')
const search = ref('')
const draft = ref('')
const inviteUsername = ref('')
const includeNotes = ref(false)
const inviteOpen = ref(false)
const shareOpen = ref(false)
const settingsOpen = ref(false)
const removeConfirm = ref(false)
const inviteBusy = ref(false)
const shareBusy = ref(false)
const sendBusy = ref(false)
const historyBusy = ref(false)
const hasOlder = ref(false)
const dialogError = ref('')
const sendError = ref('')
const pageError = ref('')
const livePlanError = ref('')
const messageViewport = ref<HTMLElement | null>(null)
const messageEnd = ref<HTMLElement | null>(null)
let poller: ReturnType<typeof setInterval> | undefined
const messageLoads = new Set<number>()
const livePlanLoads = new Set<number>()
const drafts = new Map<number, string>()
let selectionVersion = 0
let overviewBusy = false
let mounted = false

const activeContact = computed(() => contacts.value.find(item => item.id === activeId.value) || null)
const filteredContacts = computed(() => {
  const query = search.value.trim().toLowerCase()
  return contacts.value.filter(contact => !query || contact.displayName.toLowerCase().includes(query) || contact.username.includes(query))
})
const todayCaption = computed(() => {
  return new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: 'long', day: 'numeric',
  }).format(new Date())
})

async function request<T>(path: string, method = 'GET', data?: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method,
    signal: AbortSignal.timeout(12000),
    ...(data === undefined ? {} : { body: JSON.stringify(data), headers: { 'Content-Type': 'application/json' } }),
  })
  const result = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(result.error || '请求失败，请稍后重试。')
  return result as T
}

async function loadOverview(keepSelection = true) {
  if (overviewBusy || auth.localMode) return
  overviewBusy = true
  let selectionChanged = false
  try {
    const result = await request<Overview>('/api/connections')
    contacts.value = result.contacts
    incoming.value = result.incoming
    outgoing.value = result.outgoing
    if (!keepSelection || !contacts.value.some(contact => contact.id === activeId.value)) {
      const previousId = activeId.value
      activeId.value = contacts.value[0]?.id ?? null
      selectionChanged = previousId !== activeId.value
    }
    pageError.value = ''
  } catch (error) {
    pageError.value = messageOf(error)
  } finally {
    overviewBusy = false
  }
  if (mounted && selectionChanged && activeContact.value) await loadMessages(true)
}

async function selectContact(contact: Contact) {
  if (activeId.value === contact.id) {
    mobilePane.value = 'chat'
    return
  }
  activeId.value = contact.id
  mobilePane.value = 'chat'
  settingsOpen.value = false
  removeConfirm.value = false
  livePlan.value = null
  livePlanError.value = ''
  messages.value = []
  hasOlder.value = false
  await loadMessages(true)
  if (activeContact.value?.peerSharesToday) await loadLivePlan()
}

async function loadMessages(reset = false) {
  const contact = activeContact.value
  if (!contact || messageLoads.has(contact.id) || auth.localMode) return
  messageLoads.add(contact.id)
  const version = selectionVersion
  const firstId = messages.value[0]?.id
  const lastId = messages.value[messages.value.length - 1]?.id
  try {
    let path = `/api/connections/${contact.id}/messages`
    if (!reset && lastId) path += `?after=${lastId}&visibleFrom=${firstId}`
    else if (!reset && firstId && hasOlder.value) path += `?before=${firstId}`
    const result = await request<{ messages: ChatMessage[]; hasMore: boolean; revokedIds: number[] }>(path)
    if (version !== selectionVersion || activeId.value !== contact.id) return
    if (reset || !messages.value.length) {
      messages.value = result.messages
      hasOlder.value = result.hasMore
      await scrollToBottom()
    } else if (result.messages.length) {
      const known = new Map(messages.value.map(message => [message.id, message]))
      result.messages.forEach(message => known.set(message.id, message))
      messages.value = [...known.values()].sort((a, b) => a.id - b.id)
      await scrollToBottom()
    }
    for (const id of result.revokedIds) markRevoked(id)
    const lastIncoming = [...messages.value].reverse().find(item => item.sender !== auth.user?.username)
    const chatIsVisible = window.matchMedia('(min-width: 701px)').matches || mobilePane.value === 'chat'
    if (document.visibilityState === 'visible' && chatIsVisible && lastIncoming) {
      await request(`/api/connections/${contact.id}/read`, 'POST', { messageId: String(lastIncoming.id) })
      const currentContact = contacts.value.find(item => item.id === contact.id)
      if (currentContact) currentContact.unread = 0
    }
  } catch (error) {
    if (reset) pageError.value = messageOf(error)
  } finally {
    messageLoads.delete(contact.id)
  }
}

async function loadOlder() {
  if (!hasOlder.value || historyBusy.value || !messages.value.length || !activeContact.value) return
  const connectionId = activeContact.value.id
  const version = selectionVersion
  const firstMessageId = messages.value[0].id
  historyBusy.value = true
  const oldHeight = messageViewport.value?.scrollHeight || 0
  const oldTop = messageViewport.value?.scrollTop || 0
  try {
    const result = await request<{ messages: ChatMessage[]; hasMore: boolean }>(
      `/api/connections/${connectionId}/messages?before=${firstMessageId}`,
    )
    if (activeId.value !== connectionId || selectionVersion !== version) return
    messages.value = [...result.messages, ...messages.value]
    hasOlder.value = result.hasMore
    await new Promise(resolve => requestAnimationFrame(() => resolve(undefined)))
    if (messageViewport.value) messageViewport.value.scrollTop = oldTop + messageViewport.value.scrollHeight - oldHeight
  } catch (error) {
    pageError.value = messageOf(error)
  } finally {
    historyBusy.value = false
  }
}

function sendOnEnter(event: KeyboardEvent) {
  if (event.isComposing || event.keyCode === 229) return
  event.preventDefault()
  void sendMessage()
}

async function sendMessage() {
  if (!activeContact.value || !draft.value.trim() || sendBusy.value) return
  sendBusy.value = true
  const connectionId = activeContact.value.id
  const version = selectionVersion
  const body = draft.value.trim()
  sendError.value = ''
  try {
    const message = await request<ChatMessage>(`/api/connections/${connectionId}/messages`, 'POST', {
      body, clientId: crypto.randomUUID(),
    })
    if (activeId.value === connectionId && selectionVersion === version) {
      if (!messages.value.some(item => item.id === message.id)) messages.value.push(message)
      if (draft.value.trim() === body) draft.value = ''
      await scrollToBottom()
    }
    void loadOverview()
  } catch (error) {
    if (activeId.value === connectionId) sendError.value = messageOf(error)
  } finally {
    sendBusy.value = false
  }
}

async function invite() {
  if (inviteBusy.value) return
  inviteBusy.value = true
  dialogError.value = ''
  try {
    await request('/api/connections/invitations', 'POST', { username: inviteUsername.value })
    inviteUsername.value = ''
    inviteOpen.value = false
    await loadOverview(false)
  } catch (error) {
    dialogError.value = messageOf(error)
  } finally {
    inviteBusy.value = false
  }
}

async function respond(id: number, action: 'accept' | 'reject') {
  try {
    await request(`/api/connections/${id}/invitation`, 'PATCH', { action })
    await loadOverview(false)
  } catch (error) {
    pageError.value = messageOf(error)
  }
}

async function setSharing(enabled: boolean) {
  if (!activeContact.value) return
  const connectionId = activeContact.value.id
  shareBusy.value = true
  try {
    const result = await request<{ sharesToday: boolean }>(
      `/api/connections/${connectionId}/sharing`, 'PATCH', { enabled },
    )
    const contact = contacts.value.find(item => item.id === connectionId)
    if (contact) contact.sharesToday = result.sharesToday
    void loadOverview()
  } catch (error) {
    pageError.value = messageOf(error)
  } finally {
    shareBusy.value = false
  }
}

async function loadLivePlan() {
  const contact = activeContact.value
  if (!contact?.peerSharesToday) {
    livePlan.value = null
    return
  }
  if (livePlanLoads.has(contact.id)) return
  livePlanLoads.add(contact.id)
  const version = selectionVersion
  try {
    const result = await request<SharedPlan>(`/api/connections/${contact.id}/today`)
    if (activeId.value === contact.id && selectionVersion === version && activeContact.value?.peerSharesToday) {
      livePlan.value = result
      livePlanError.value = ''
    }
  } catch (error) {
    if (activeId.value === contact.id && selectionVersion === version) {
      livePlan.value = null
      livePlanError.value = messageOf(error)
    }
    if (activeId.value === contact.id && error instanceof Error && /关闭|未开放/.test(error.message)) {
      const currentContact = contacts.value.find(item => item.id === contact.id)
      if (currentContact) currentContact.peerSharesToday = false
      livePlanError.value = ''
    }
  } finally {
    livePlanLoads.delete(contact.id)
  }
}

async function openShare() {
  shareBusy.value = true
  dialogError.value = ''
  includeNotes.value = false
  sharePreview.value = null
  shareOpen.value = true
  try {
    const day = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Shanghai' }).format(new Date())
    sharePreview.value = await request<PlanReply>(`/api/planner/day/${day}`)
  } catch (error) {
    dialogError.value = messageOf(error)
  } finally {
    shareBusy.value = false
  }
}

async function shareToday() {
  if (!activeContact.value || shareBusy.value) return
  const connectionId = activeContact.value.id
  const version = selectionVersion
  shareBusy.value = true
  dialogError.value = ''
  try {
    const message = await request<ChatMessage>(
      `/api/connections/${connectionId}/share-today`, 'POST',
      { clientId: crypto.randomUUID(), includeNotes: includeNotes.value },
    )
    if (activeId.value === connectionId && selectionVersion === version) {
      if (!messages.value.some(item => item.id === message.id)) messages.value.push(message)
      shareOpen.value = false
      await scrollToBottom()
    }
    void loadOverview()
  } catch (error) {
    if (activeId.value === connectionId) dialogError.value = messageOf(error)
  } finally {
    shareBusy.value = false
  }
}

function openSnapshot(message: ChatMessage) {
  snapshotMessageId.value = message.id
  snapshotView.value = message.plan || null
}

function markRevoked(id: number) {
  const message = messages.value.find(item => item.id === id)
  if (message) {
    message.revoked = true
    message.plan = undefined
  }
  if (snapshotMessageId.value === id) snapshotView.value = null
}

async function revokePlan(id: number) {
  if (!activeContact.value) return
  try {
    await request(`/api/connections/${activeContact.value.id}/messages/${id}`, 'DELETE')
    markRevoked(id)
  } catch (error) {
    pageError.value = messageOf(error)
  }
}

async function removeContact() {
  if (!activeContact.value) return
  try {
    await request(`/api/connections/${activeContact.value.id}`, 'DELETE')
    activeId.value = null
    messages.value = []
    livePlan.value = null
    settingsOpen.value = false
    removeConfirm.value = false
    mobilePane.value = 'contacts'
    await loadOverview(false)
  } catch (error) {
    pageError.value = messageOf(error)
  }
}

async function scrollToBottom() {
  await new Promise(resolve => requestAnimationFrame(() => resolve(undefined)))
  messageEnd.value?.scrollIntoView({ block: 'end', behavior: 'smooth' })
}

function previewText(message: ChatMessage) {
  if (message.revoked) return '计划分享已撤回'
  return message.kind === 'plan' ? '分享了今日计划' : message.body
}
function timeLabel(value: string) {
  const normalized = /(?:Z|[+-]\d{2}:\d{2})$/.test(value) ? value : `${value}+08:00`
  const date = new Date(normalized)
  return Number.isNaN(date.getTime()) ? '' : new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit',
  }).format(date)
}
function avatarLetter(name: string) { return Array.from(name.trim())[0] || '?' }
function messageOf(error: unknown) { return error instanceof Error ? error.message : '请求失败，请稍后重试。' }

watch(activeId, (id, previous) => {
  selectionVersion += 1
  if (previous) drafts.set(previous, draft.value)
  draft.value = id ? drafts.get(id) || '' : ''
  messages.value = []
  snapshotView.value = null
  sendError.value = ''
  settingsOpen.value = false
  hasOlder.value = false
}, { flush: 'sync' })
watch(() => [activeContact.value?.id, activeContact.value?.peerSharesToday] as const, ([id, shares]) => {
  if (id && shares) void loadLivePlan()
  else livePlan.value = null
})
onMounted(async () => {
  await loadOverview()
  mounted = true
  if (activeContact.value) {
    await loadMessages(true)
    if (activeContact.value.peerSharesToday) await loadLivePlan()
  }
  poller = window.setInterval(() => {
    if (document.visibilityState !== 'visible' || auth.localMode) return
    void loadOverview()
    if (activeContact.value && (window.matchMedia('(min-width: 701px)').matches || mobilePane.value === 'chat')) void loadMessages()
    if (activeContact.value?.peerSharesToday) void loadLivePlan()
  }, 5000)
})
onBeforeUnmount(() => {
  if (poller !== undefined) window.clearInterval(poller)
})
</script>

<style>
.connection-screen {
  --ink: #293b33;
  --muted: #708078;
  --line: #dbe4df;
  --coral: #eb9388;
  box-sizing: border-box;
  min-height: 100dvh;
  padding: 0 28px 24px 116px;
  color: var(--ink);
  background: #f5f8f7;
  font: 14px/1.5 "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
}
.connection-screen *, .connection-screen *::before, .connection-screen *::after { box-sizing: border-box; letter-spacing: 0; }
.connection-screen button, .connection-screen input, .connection-screen textarea { font: inherit; }
.connection-screen button { color: inherit; cursor: pointer; -webkit-tap-highlight-color: transparent; }
.connection-screen button:disabled { opacity: .48; cursor: default; }
.connection-screen a { color: inherit; text-decoration: none; }
.connection-screen :focus-visible { outline: 3px solid #347b92; outline-offset: 3px; }
.connection-content { max-width: 1640px; height: calc(100dvh - 24px); min-height: 660px; margin: 0 auto; display: flex; flex-direction: column; }
.connection-topbar { height: 74px; flex-shrink: 0; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--line); }
.connection-brand { font: 700 25px/1 Georgia, "Times New Roman", serif; }
.connection-brand span { color: var(--coral); }
.connection-back { min-height: 44px; display: inline-flex; align-items: center; gap: 9px; color: #62746a; font-size: 13px; }
.connection-heading { min-height: 98px; display: flex; align-items: center; justify-content: space-between; gap: 16px; }
.connection-eyebrow { margin: 0 0 2px; color: var(--muted); font-size: 11px; }
.connection-heading h1 { margin: 0; font-size: 24px; line-height: 1.3; }
.connection-add-button { display: inline-flex; align-items: center; justify-content: center; gap: 9px; min-height: 42px; padding: 0 15px; border: 1px solid #e58a80; border-radius: 5px; color: #462d2a !important; background: #f19a8f; font-size: 12px !important; font-weight: 600 !important; }
.connection-add-button:hover { background: #e88c80; }
.connection-workspace { display: grid; flex: 1; min-height: 0; grid-template-rows: minmax(0, 1fr); grid-template-columns: minmax(230px, 270px) minmax(330px, 1fr) minmax(260px, 315px); border: 1px solid #d6e0da; border-radius: 7px; background: #fff; overflow: hidden; }
.connection-workspace:not(.has-contact) .connection-chat-placeholder { grid-column: 2 / -1; border-right: 0; }
.connection-contacts { min-width: 0; min-height: 0; display: flex; flex-direction: column; border-right: 1px solid var(--line); overflow-y: auto; }
.connection-list-heading { display: flex; align-items: center; gap: 8px; padding: 17px 14px 12px; }
.connection-list-heading h2 { margin: 0; font-size: 15px; }
.connection-list-heading > span { color: #77877e; font-size: 11px; }
.connection-list-heading .icon-button { margin-left: auto; }
.connection-search { min-height: 38px; display: flex; align-items: center; gap: 8px; margin: 0 12px 12px; padding: 0 10px; border: 1px solid #dce5df; border-radius: 5px; background: #fbfcfb; color: #839188; }
.connection-search svg { flex: 0 0 auto; font-size: 12px; }
.connection-search input { width: 100%; min-width: 0; height: 34px; border: 0; outline: 0; background: transparent; color: var(--ink); font-size: 12px; }
.connection-search:focus-within { outline: 3px solid #347b92; outline-offset: 2px; }
.connection-search input:focus-visible { outline: 0; }
.connection-contact-list { display: flex; flex-direction: column; min-height: 0; overflow-y: auto; }
.connection-contact { position: relative; min-height: 68px; display: flex; align-items: center; gap: 10px; width: 100%; padding: 9px 12px; border: 0; border-left: 3px solid transparent; background: transparent; text-align: left; }
.connection-contact:hover { background: #f7faf8; }
.connection-contact.selected { border-left-color: #e98e83; background: #fff6f4; }
.connection-avatar { flex: 0 0 38px; width: 38px; height: 38px; display: grid; place-items: center; border-radius: 50%; color: #78544d; background: #f6e0db; font-size: 15px; font-weight: 600; }
.avatar-active { box-shadow: 0 0 0 2px #f19a8f; }
.connection-contact-copy { display: grid; flex: 1; min-width: 0; gap: 3px; }
.connection-contact-title { display: flex; align-items: center; justify-content: space-between; gap: 8px; min-width: 0; }
.connection-contact-title strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 12px; font-weight: 600; }
.connection-contact-title time { flex: 0 0 auto; color: #89958e; font-size: 10px; font-variant-numeric: tabular-nums; }
.connection-contact-preview { overflow: hidden; color: #77857d; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.connection-unread { flex: 0 0 auto; min-width: 18px; height: 18px; display: grid; place-items: center; padding: 0 4px; border-radius: 10px; color: #fff; background: #e57f75; font-size: 10px; }
.connection-invitations, .connection-outgoing { padding: 12px; border-top: 1px solid #e7ede9; }
.connection-invitations h3, .connection-outgoing h3 { display: flex; align-items: center; gap: 7px; margin: 0 0 8px; color: #68796f; font-size: 11px; font-weight: 600; }
.connection-invitations h3 span { color: #a65047; }
.connection-request, .connection-outgoing-row { display: flex; align-items: center; gap: 8px; padding: 7px 0; }
.connection-request .connection-avatar, .connection-outgoing-row .connection-avatar { width: 32px; height: 32px; flex-basis: 32px; font-size: 12px; }
.connection-request > div, .connection-outgoing-row > span:nth-child(2) { display: grid; flex: 1; min-width: 0; }
.connection-request strong, .connection-outgoing-row strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.connection-request small, .connection-outgoing-row small { color: #89958e; font-size: 10px; }
.connection-accept, .connection-reject { width: 32px; height: 32px; border: 1px solid #dce5df; border-radius: 5px; background: #fff; font-size: 12px !important; }
.connection-accept { color: #4d765b !important; }
.connection-reject { color: #a4564c !important; }
.connection-pending { color: #9b8053; font-size: 10px; white-space: nowrap; }
.connection-list-empty { min-height: 160px; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 10px; color: #8a9890; font-size: 11px; }
.connection-list-empty svg { font-size: 21px; color: #89a396; }
.connection-chat { position: relative; min-width: 0; min-height: 0; display: flex; flex-direction: column; border-right: 1px solid var(--line); }
.connection-chat-heading { min-height: 68px; display: flex; align-items: center; gap: 10px; padding: 10px 15px; border-bottom: 1px solid var(--line); }
.connection-chat-heading .connection-avatar { width: 36px; height: 36px; flex-basis: 36px; }
.connection-chat-person { flex: 1; min-width: 0; }
.connection-chat-person h2 { margin: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 14px; }
.connection-chat-person span { color: #839087; font-size: 10px; }
.connection-plan-toggle { display: none; align-items: center; gap: 7px; min-height: 38px; padding: 0 10px; border: 1px solid #dce5df; border-radius: 5px; background: #fff; color: #5e7668 !important; font-size: 11px !important; }
.connection-menu { flex: 0 0 auto; }
.connection-settings { position: absolute; z-index: 3; top: 58px; right: 12px; width: min(310px, calc(100% - 24px)); padding: 14px; border: 1px solid #d6e0da; border-radius: 6px; background: #fff; box-shadow: 0 8px 26px #263a3218; }
.connection-share-setting { display: flex; align-items: center; justify-content: space-between; gap: 14px; padding: 11px 0; }
.connection-share-setting > span { display: grid; gap: 3px; min-width: 0; }
.connection-share-setting strong { font-size: 11px; font-weight: 600; }
.connection-share-setting small { color: #7b8980; font-size: 10px; line-height: 1.5; }
.connection-share-setting input { flex: 0 0 auto; width: 40px; height: 22px; appearance: none; margin: 0; border: 1px solid #a7b4ac; border-radius: 14px; background: #e0e7e2; cursor: pointer; position: relative; }
.connection-share-setting input::after { content: ""; position: absolute; top: 2px; left: 2px; width: 16px; height: 16px; border-radius: 50%; background: #fff; box-shadow: 0 1px 2px #24372d30; transition: transform .16s ease; }
.connection-share-setting input:checked { border-color: #5a8167; background: #5a8167; }
.connection-share-setting input:checked::after { transform: translateX(17px); }
.connection-remove { width: 100%; min-height: 38px; border: 0; border-top: 1px solid #e7ede9; background: transparent; text-align: left; color: #a44e46 !important; font-size: 11px !important; }
.connection-remove-confirm { display: grid; gap: 9px; padding-top: 8px; color: #79524c; font-size: 10px; }
.connection-remove-confirm button { justify-self: end; min-height: 34px; padding: 0 11px; border: 1px solid #a94d45; border-radius: 4px; color: #fff !important; background: #a94d45; font-size: 10px !important; }
.connection-messages { flex: 1; min-height: 0; display: flex; flex-direction: column; gap: 13px; overflow-y: auto; padding: 16px 15px; scroll-behavior: smooth; }
.connection-load-older { align-self: center; min-height: 34px; padding: 0 10px; border: 1px solid #e0e7e2; border-radius: 4px; background: #fff; color: #708078; font-size: 10px !important; }
.connection-chat-empty { flex: 1; min-height: 230px; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; color: #78877e; }
.connection-chat-empty img { width: 82px; height: 86px; object-fit: contain; margin-bottom: 6px; }
.connection-chat-empty strong { color: #53675a; font-size: 13px; }
.connection-chat-empty span { font-size: 11px; }
.connection-message { max-width: 86%; display: flex; align-items: flex-end; gap: 8px; }
.connection-message.mine { align-self: flex-end; }
.message-avatar { width: 28px; height: 28px; flex-basis: 28px; font-size: 11px; }
.connection-bubble-wrap { min-width: 0; }
.connection-bubble { width: fit-content; max-width: 100%; margin: 0; padding: 10px 12px; border: 1px solid #e0e8e2; border-radius: 7px 7px 7px 2px; background: #f7faf8; color: #35483d; font-size: 12px; line-height: 1.65; overflow-wrap: anywhere; white-space: pre-wrap; }
.mine .connection-bubble { margin-left: auto; border-color: #f0d2cc; border-radius: 7px 7px 2px 7px; background: #fff2ef; }
.message-revoked .connection-bubble { color: #89958d; background: #f5f6f5; }
.connection-plan-message { width: min(290px, 70vw); min-height: 66px; display: flex; align-items: center; gap: 10px; padding: 9px 11px; border: 1px solid #d8e4db; border-radius: 6px; background: #f8fbf8; text-align: left; }
.mine .connection-plan-message { border-color: #edc9c2; background: #fff7f5; }
.shared-plan-icon { flex: 0 0 34px; width: 34px; height: 34px; display: grid; place-items: center; border-radius: 5px; color: #8c594e; background: #f9e2dd; }
.shared-plan-copy { display: grid; flex: 1; min-width: 0; gap: 3px; }
.shared-plan-copy strong { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 11px; }
.shared-plan-copy small { color: #7d8c82; font-size: 10px; }
.connection-plan-message > svg { flex: 0 0 auto; color: #89988f; font-size: 11px; }
.connection-message-meta { display: flex; align-items: center; gap: 9px; margin-top: 4px; color: #98a39c; font-size: 9px; }
.mine .connection-message-meta { justify-content: flex-end; }
.connection-revoke { padding: 0; border: 0; color: #9c5b52 !important; background: transparent; font-size: 9px !important; }
.connection-composer { display: flex; align-items: flex-end; gap: 8px; padding: 11px 12px; border-top: 1px solid var(--line); }
.connection-send-error { margin: 0; padding: 8px 12px; color: #a03831; background: #fff0ee; font-size: 12px; }
.connection-composer textarea { flex: 1; min-width: 0; max-height: 116px; min-height: 42px; resize: vertical; padding: 10px 11px; border: 1px solid #d9e3dc; border-radius: 5px; color: var(--ink); background: #fbfcfb; line-height: 1.5; font-size: 12px; }
.connection-composer textarea::placeholder { color: #9aa69f; }
.connection-share-button, .connection-send-button { flex: 0 0 42px; width: 42px; height: 42px; display: grid; place-items: center; border: 1px solid #d9e3dc; border-radius: 5px; background: #fff; color: #66806e !important; font-size: 15px !important; }
.connection-send-button { border-color: #e8887d; background: #f1978d; color: #48302c !important; }
.connection-share-button:hover { background: #f0f6f1; }
.connection-send-button:hover:not(:disabled) { background: #e7867b; }
.connection-chat-placeholder { border-right: 1px solid var(--line); }
.connection-chat-placeholder > div { margin: auto; display: flex; flex-direction: column; align-items: center; gap: 8px; color: #839087; text-align: center; }
.connection-chat-placeholder svg { color: #8ea196; font-size: 25px; }
.connection-chat-placeholder h2 { margin: 5px 0 0; color: #47594e; font-size: 16px; }
.connection-chat-placeholder span { font-size: 11px; }
.connection-plan { min-width: 0; min-height: 0; overflow-y: auto; padding: 16px 14px; background: #fbfcfb; }
.connection-mobile-plan { display: none; }
.connection-plan-heading { display: flex; align-items: center; justify-content: space-between; gap: 10px; padding: 2px 0 14px; border-bottom: 1px solid var(--line); }
.connection-plan-heading p { margin: 0 0 2px; color: #859189; font-size: 10px; }
.connection-plan-heading h2 { margin: 0; overflow-wrap: anywhere; font-size: 14px; }
.connection-plan-heading span { color: #829087; font-size: 10px; }
.connection-plan-heading > svg { color: #a76a5e; }
.connection-plan-sections { display: grid; gap: 10px; padding-top: 12px; }
.connection-plan-sections > h3 { margin: 0 0 2px; color: #405348; font-size: 13px; }
.connection-plan-section { min-width: 0; padding: 10px 10px 7px; border-left: 3px solid var(--accent); background: #fff; }
.connection-plan-section.color-rose { --accent: #e88791; }
.connection-plan-section.color-gold { --accent: #dfbc56; }
.connection-plan-section.color-sage { --accent: #90b887; }
.connection-plan-section.color-blue { --accent: #89b2d0; }
.connection-plan-section.color-lilac { --accent: #b899c5; }
.connection-plan-section.color-teal { --accent: #83b9ad; }
.connection-plan-section > header { display: flex; justify-content: space-between; gap: 8px; padding-bottom: 7px; color: #3e5045; font-size: 11px; font-weight: 600; }
.connection-plan-section > header small { color: #849187; font-size: 10px; font-weight: 400; }
.connection-plan-section article { display: flex; align-items: flex-start; gap: 8px; padding: 7px 0; border-top: 1px solid #edf1ee; }
.shared-task-check { flex: 0 0 15px; width: 15px; height: 15px; display: grid; place-items: center; margin-top: 1px; border: 1px solid var(--accent); border-radius: 4px; color: #426b50; font-size: 10px; }
.connection-plan-section article > div { display: grid; gap: 3px; min-width: 0; }
.connection-plan-section article strong { color: #43544a; font-size: 10px; font-weight: 500; overflow-wrap: anywhere; }
.connection-plan-section article small { color: #819087; font-size: 9px; }
.connection-plan-section article p { margin: 1px 0 0; color: #7f8c83; font-size: 9px; line-height: 1.5; overflow-wrap: anywhere; white-space: pre-wrap; }
.shared-task-done strong { color: #929d95 !important; text-decoration: line-through; }
.shared-task-done .shared-task-check { background: #e6f0e7; }
.connection-plan-section-empty { margin: 0; color: #94a097; font-size: 10px; }
.connection-sharing-control { margin-top: 16px; padding-top: 7px; border-top: 1px solid var(--line); }
.connection-plan-private { min-height: 180px; display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 10px; color: #7d8c82; font-size: 11px; text-align: center; }
.connection-plan-private svg { color: #87978e; font-size: 19px; }
.connection-plan-loading { min-height: 180px; display: flex; align-items: center; justify-content: center; gap: 8px; color: #829187; font-size: 11px; }
.connection-plan-error { padding: 10px; border-left: 3px solid #d57168; color: #a03831; background: #fff0ee; font-size: 11px; }
.connection-footer { display: flex; align-items: center; gap: 7px; min-height: 42px; color: #85938a; font-size: 10px; }
.connection-footer svg { color: #72917d; font-size: 10px; }
.connection-unavailable { max-width: 620px; margin: 58px auto; display: flex; align-items: center; gap: 17px; padding: 23px; border: 1px solid #dce5df; border-radius: 6px; background: #fff; }
.connection-unavailable > svg { color: #758a7c; font-size: 21px; }
.connection-unavailable > div { flex: 1; }
.connection-unavailable h2 { margin: 0 0 4px; font-size: 15px; }
.connection-unavailable p { margin: 0; color: #78877e; font-size: 11px; }
.connection-unavailable > a { color: #4c705b; font-size: 11px; white-space: nowrap; }
.connection-alert { margin: 0 0 12px; padding: 10px 12px; border: 1px solid #e6aaa1; border-radius: 4px; color: #a03831; background: #fff0ee; font-size: 12px; }
.connection-dialog-form { display: grid; gap: 15px; padding-top: 12px; }
.connection-dialog-form > label:not(.connection-include-notes) { display: grid; gap: 7px; color: #53665a; font-size: 12px; }
.connection-dialog-form input:not([type="checkbox"]) { min-height: 42px; padding: 9px 11px; border: 1px solid #cbd9d1; border-radius: 5px; background: #fbfcfb; color: #293b33; }
.connection-dialog-note { margin: 0; color: #738279; font-size: 11px; line-height: 1.6; }
.connection-dialog-actions { display: flex; justify-content: flex-end; gap: 9px; padding-top: 5px; border-top: 1px solid #e2e9e4; }
.connection-dialog-actions button { min-height: 40px; }
.connection-dialog-actions .account-secondary, .connection-dialog-actions .account-primary {
  display: inline-flex; align-items: center; justify-content: center; gap: 8px; padding: 0 14px;
  border: 1px solid #d6e0da; border-radius: 5px; color: #405348 !important; background: #fff;
  font-size: 12px !important;
}
.connection-dialog-actions .account-primary { border-color: #e88c81; color: #472f2a !important; background: #f1978d; font-weight: 600 !important; }
.connection-dialog-actions .account-primary:hover:not(:disabled) { background: #e9877c; }
.connection-dialog-actions .account-secondary:hover { background: #f3f7f4; }
.connection-dialog-actions .account-secondary, .connection-dialog-actions .account-primary { font-size: 12px !important; }
.connection-include-notes { display: flex; align-items: center; gap: 9px; color: #45594c; font-size: 12px; }
.connection-include-notes input { width: 17px; height: 17px; accent-color: #5a8167; }
.connection-share-preview { display: grid; gap: 6px; padding: 13px; border: 1px solid #dce5df; border-radius: 5px; background: #fbfcfb; }
.connection-share-preview strong { font-size: 13px; }
.connection-share-preview span, .connection-share-preview p { margin: 0; color: #748278; font-size: 10px; }
.connection-snapshot-heading { padding: 5px 0 10px; color: #75847a; font-size: 11px; }
.connection-mobile-nav { display: none; }
.connection-mobile-back { display: none; }
@media (max-width: 1100px) {
  .connection-screen { padding-right: 18px; padding-left: 106px; }
  .connection-workspace { grid-template-columns: minmax(190px, 230px) minmax(0, 1fr); }
  .connection-workspace > .connection-plan:not(.connection-mobile-plan) { display: none; }
  .connection-plan-toggle { display: inline-flex; }
  .connection-workspace.pane-plan > .connection-chat { display: none; }
  .connection-workspace.pane-plan > .connection-mobile-plan { display: block; grid-column: 2; }
  .connection-mobile-plan-heading { display: flex; align-items: center; gap: 9px; margin-bottom: 12px; }
  .connection-mobile-plan-heading h2 { margin: 0; font-size: 16px; }
  .connection-mobile-plan-heading span { color: #65766b; font-size: 12px; }
  .connection-mobile-plan-heading .connection-mobile-back { display: grid; place-items: center; width: 40px; height: 42px; border: 0; background: transparent; }
}
@media (min-width: 701px) and (max-width: 760px) {
  .connection-rail { display: flex; }
}
@media (max-width: 700px) {
  .connection-screen { min-height: 100dvh; padding: 0 14px calc(76px + env(safe-area-inset-bottom)); }
  .connection-rail { display: none; }
  .connection-content { height: auto; min-height: calc(100dvh - 76px - env(safe-area-inset-bottom)); }
  .connection-topbar { height: 60px; }
  .connection-brand { font-size: 22px; }
  .connection-back { min-height: 44px; font-size: 12px; }
  .connection-heading { min-height: 76px; }
  .connection-eyebrow { font-size: 10px; }
  .connection-heading h1 { font-size: 21px; }
  .connection-add-button { min-height: 40px; padding: 0 11px; font-size: 11px !important; }
  .connection-workspace { display: block; min-height: calc(100dvh - 224px - env(safe-area-inset-bottom)); border-radius: 6px; overflow: hidden; }
  .connection-contacts { height: 100%; min-height: 430px; border-right: 0; }
  .connection-workspace.has-contact.pane-chat .connection-contacts, .connection-workspace.has-contact.pane-plan .connection-contacts { display: none; }
  .connection-workspace.pane-contacts .connection-chat { display: none; }
  .connection-workspace:not(.has-contact) .connection-chat, .connection-workspace:not(.has-contact) .connection-mobile-plan { display: none; }
  .connection-workspace.pane-plan .connection-chat { display: none; }
  .connection-chat { min-height: min(68dvh, 720px); height: calc(100dvh - 230px - env(safe-area-inset-bottom)); border-right: 0; }
  .connection-chat-heading { min-height: 62px; padding: 8px 9px; }
  .connection-mobile-back { display: grid; place-items: center; flex: 0 0 40px; width: 40px; height: 42px; border: 0; border-radius: 5px; background: transparent; color: #65776c !important; font-size: 15px !important; }
  .connection-chat-heading .connection-mobile-back { display: grid; }
  .connection-plan-toggle { min-height: 38px; padding: 0 8px; font-size: 10px !important; }
  .connection-menu { width: 34px; height: 38px; }
  .connection-messages { gap: 12px; padding: 12px 10px; }
  .connection-message { max-width: 92%; }
  .connection-composer { padding: 9px; gap: 6px; padding-bottom: calc(9px + env(safe-area-inset-bottom)); }
  .connection-share-button, .connection-send-button { flex-basis: 42px; width: 42px; height: 42px; }
  .connection-plan.connection-mobile-plan { display: block; min-height: 430px; height: calc(100dvh - 230px - env(safe-area-inset-bottom)); padding: 11px; }
  .connection-mobile-plan-heading { display: flex; align-items: center; gap: 9px; min-height: 48px; margin: -3px 0 8px; }
  .connection-mobile-plan-heading h2 { margin: 0; font-size: 14px; }
  .connection-mobile-plan-heading span { color: #849189; font-size: 10px; }
  .connection-plan-footer, .connection-footer { font-size: 9px; }
  .connection-mobile-nav { position: fixed; z-index: 20; right: 0; bottom: 0; left: 0; display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); min-height: calc(60px + env(safe-area-inset-bottom)); padding: 5px 5px calc(5px + env(safe-area-inset-bottom)); border-top: 1px solid #dce3df; background: #fff; }
  .connection-mobile-nav a { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 3px; min-width: 0; min-height: 48px; border-radius: 5px; color: #7d8981; font-size: 10px; }
  .connection-mobile-nav a svg { font-size: 16px; }
  .connection-mobile-nav a.selected { color: #9b4e45; background: #fce8e4; }
  .connection-footer { padding-top: 6px; min-height: 32px; }
  .connection-unavailable { margin: 28px 0; flex-wrap: wrap; padding: 17px; }
  .connection-unavailable > a { margin-left: 36px; }
  .connection-contact { min-height: 70px; padding: 10px 12px; }
  .connection-search input, .connection-composer textarea, .connection-dialog-form input:not([type="checkbox"]) { font-size: 16px; }
  .connection-bubble, .connection-contact-title strong, .connection-chat-person h2 { font-size: 15px; }
  .connection-contact-preview, .shared-plan-copy strong, .connection-plan-section > header { font-size: 13px; }
  .connection-plan-section article strong, .connection-share-setting strong { font-size: 14px; }
  .connection-plan-section article small, .connection-share-setting small { font-size: 12px; color: #65756b; }
  .connection-revoke { min-height: 24px; font-size: 11px !important; }
  .connection-accept, .connection-reject { width: 40px; height: 40px; }
}
@media (max-width: 380px) {
  .connection-screen { padding-right: 10px; padding-left: 10px; }
  .connection-contact-title time { display: none; }
  .connection-chat-heading { gap: 6px; }
  .connection-chat-heading .connection-avatar { width: 32px; height: 32px; flex-basis: 32px; }
  .connection-plan-toggle { gap: 5px; padding: 0 7px; }
}
@media (prefers-reduced-motion: reduce) {
  .connection-screen *, .connection-screen *::before, .connection-screen *::after { scroll-behavior: auto !important; transition-duration: .01ms !important; animation-duration: .01ms !important; }
}
</style>
