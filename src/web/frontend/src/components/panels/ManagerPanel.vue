<template>
<section class="h-full flex gap-6">
        <aside class="w-[400px] glass-panel flex flex-col h-full shrink-0 p-5 gap-4 overflow-y-auto custom-scrollbar">
          <h2 class="panel-title"><LayoutDashboard class="w-5 h-5 text-tech-cyan" /> 管理者首页</h2>

          <div class="p-4 rounded-xl border border-tech-cyan/25 bg-gradient-to-br from-slate-900/90 to-slate-800/60 space-y-3">
            <div class="flex items-center justify-between">
              <span class="text-[11px] text-slate-300 font-mono">风险总览</span>
              <span class="px-2 py-1 rounded border border-tech-cyan/40 bg-tech-cyan/10 text-tech-cyan text-[11px] font-mono">
                {{ managerRiskSnapshot.level }}色倾向
              </span>
            </div>
            <div class="grid grid-cols-3 gap-2">
              <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-2">
                <div class="text-[10px] text-slate-400 font-mono">风险分</div>
                <div class="text-lg text-white font-mono">{{ managerRiskSnapshot.riskScore }}</div>
              </div>
              <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-2">
                <div class="text-[10px] text-slate-400 font-mono">高风险区</div>
                <div class="text-lg text-amber-300 font-mono">{{ managerRiskSnapshot.highRiskZoneCount }}</div>
              </div>
              <div class="rounded-lg border border-slate-700 bg-slate-900/60 p-2">
                <div class="text-[10px] text-slate-400 font-mono">状态</div>
                <div class="text-sm text-emerald-300 font-mono mt-1">{{ managerRiskSnapshot.statusText }}</div>
              </div>
            </div>
            <div class="text-xs leading-6 text-slate-200 bg-slate-900/50 border border-slate-700 rounded-lg p-3">
              {{ managerOneLineConclusion }}
            </div>
          </div>

          <div class="p-4 rounded-xl border border-tech-cyan/20 bg-slate-900/50 space-y-3">
            <div class="flex items-center gap-2 text-tech-cyan text-sm font-mono">
              <Megaphone class="w-4 h-4" />
              预警发布中心
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">发布对象</label>
              <input v-model="managerNoticeTarget" type="text" class="tech-input" />
            </div>
            <div class="space-y-2">
              <label class="text-[10px] font-mono text-slate-400 uppercase tracking-widest">发布渠道</label>
              <select v-model="managerNoticeChannel" class="tech-input">
                <option value="平台公告">平台公告</option>
                <option value="短信">短信</option>
                <option value="邮件">邮件</option>
                <option value="值班群">值班群</option>
              </select>
            </div>
            <div class="grid grid-cols-2 gap-2">
              <button class="tech-btn ghost-btn w-full flex items-center justify-center gap-2" @click="generateManagerNotice">
                <FileText class="w-4 h-4" /> 生成文案
              </button>
              <button class="tech-btn primary-btn w-full flex items-center justify-center gap-2" @click="publishManagerNotice">
                <Megaphone class="w-4 h-4" /> 发布并留痕
              </button>
            </div>
            <textarea v-model="managerNoticeDraft" class="w-full h-32 tech-input !leading-6" placeholder="点击“生成文案”自动填写预警内容"></textarea>
          </div>

          <button class="tech-btn ghost-btn w-full flex items-center justify-center gap-2" @click="exportManagerBrief">
            <Download class="w-4 h-4" /> 导出评审简报（TXT）
          </button>
        </aside>

        <main class="flex-1 min-w-0 flex flex-col gap-4">
          <div class="glass-panel p-4 h-[56%] min-h-[280px] flex flex-col">
            <div class="flex items-center gap-3 mb-3">
              <Building2 class="w-5 h-5 text-tech-cyan" />
              <h2 class="font-display text-base tracking-wider text-white m-0">区域责任制视图（分区风险 + 责任单位）</h2>
            </div>
            <div class="flex-1 overflow-auto custom-scrollbar border border-slate-800 rounded-xl">
              <table class="w-full text-xs font-mono">
                <thead class="sticky top-0 bg-slate-900 text-slate-300">
                  <tr>
                    <th class="text-left p-3 border-b border-slate-800">区域</th>
                    <th class="text-left p-3 border-b border-slate-800">风险分</th>
                    <th class="text-left p-3 border-b border-slate-800">风险等级</th>
                    <th class="text-left p-3 border-b border-slate-800">责任单位</th>
                    <th class="text-left p-3 border-b border-slate-800">建议动作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="z in managerZoneResponsibilities" :key="z.name" class="odd:bg-slate-900/30">
                    <td class="p-3 border-b border-slate-800/70 text-slate-200">{{ z.name }}</td>
                    <td class="p-3 border-b border-slate-800/70 text-tech-cyan">{{ z.score }}</td>
                    <td class="p-3 border-b border-slate-800/70" :class="z.levelClass">{{ z.level }}</td>
                    <td class="p-3 border-b border-slate-800/70 text-slate-300">{{ z.agency }}</td>
                    <td class="p-3 border-b border-slate-800/70 text-slate-400">{{ z.action }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          <div class="glass-panel p-4 h-[44%] min-h-[200px] flex flex-col">
            <div class="flex items-center justify-between gap-3 mb-3">
              <div class="flex items-center gap-3">
                <LineChart class="w-5 h-5 text-tech-cyan" />
                <h2 class="font-display text-base tracking-wider text-white m-0">预警发布记录</h2>
              </div>
              <button class="px-3 py-1 rounded border border-tech-cyan/40 text-tech-cyan text-[11px] font-mono hover:bg-tech-cyan/10" @click="generateManagerNotice">
                更新建议文案
              </button>
            </div>

            <div v-if="managerPublishRecords.length === 0" class="flex-1 flex items-center justify-center text-slate-500 font-mono text-sm">
              暂无发布记录，点击左侧“发布并留痕”开始沉淀管理闭环
            </div>

            <div v-else class="flex-1 overflow-auto custom-scrollbar space-y-2">
              <div v-for="r in managerPublishRecords" :key="r.id" class="p-3 rounded-lg border border-slate-800 bg-slate-900/40 flex items-center justify-between gap-3">
                <div class="text-xs font-mono text-slate-300">{{ r.time }} | {{ r.target }}</div>
                <div class="text-[11px] font-mono text-slate-400">{{ r.channel }}</div>
                <div class="px-2 py-1 rounded border border-emerald-400/40 bg-emerald-500/10 text-emerald-300 text-[11px] font-mono">{{ r.status }}</div>
              </div>
            </div>
          </div>
        </main>
      </section>
</template>

<script setup>
import { LayoutDashboard, Megaphone, FileText, Download, Building2, LineChart } from 'lucide-vue-next'
import { useManager } from '../../composables/useManager'

const {
  managerNoticeDraft,
  managerNoticeTarget,
  managerNoticeChannel,
  managerPublishRecords,
  managerRiskSnapshot,
  managerZoneResponsibilities,
  managerOneLineConclusion,
  generateManagerNotice,
  publishManagerNotice,
  exportManagerBrief
} = useManager()
</script>
