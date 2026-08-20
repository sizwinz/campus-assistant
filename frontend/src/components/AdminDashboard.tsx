'use client'

import { useState, useEffect } from 'react'
import {
  MessageSquare,
  Users,
  FileText,
  AlertTriangle,
  TrendingUp,
  Globe,
  RefreshCw,
} from 'lucide-react'
import { adminApi } from '@/lib/api'
import type { DashboardStats } from '@/lib/types'

export default function AdminDashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [credentials, setCredentials] = useState({ username: '', password: '' })
  const [isLoggedIn, setIsLoggedIn] = useState(false)

  const fetchStats = async () => {
    setLoading(true)
    try {
      const data = await adminApi.getDashboard(
        credentials.username,
        credentials.password
      )
      setStats(data)
      setError(null)
    } catch (err) {
      setError('Failed to load dashboard. Check your credentials.')
    } finally {
      setLoading(false)
    }
  }

  const handleLogin = (e: React.FormEvent) => {
    e.preventDefault()
    setIsLoggedIn(true)
    fetchStats()
  }

  if (!isLoggedIn) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow-lg w-full max-w-md">
          <h1 className="text-2xl font-bold text-gray-900 mb-6 text-center">
            Admin Dashboard
          </h1>
          <form onSubmit={handleLogin} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Username
              </label>
              <input
                type="text"
                value={credentials.username}
                onChange={(e) =>
                  setCredentials({ ...credentials, username: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Password
              </label>
              <input
                type="password"
                value={credentials.password}
                onChange={(e) =>
                  setCredentials({ ...credentials, password: e.target.value })
                }
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                required
              />
            </div>
            <button
              type="submit"
              className="w-full py-2 px-4 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition-colors"
            >
              Login
            </button>
          </form>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-primary-600" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-4" />
          <p className="text-red-600">{error}</p>
          <button
            onClick={() => setIsLoggedIn(false)}
            className="mt-4 text-primary-600 hover:underline"
          >
            Try again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Admin Dashboard</h1>
            <p className="text-gray-500">Campus Assistant Analytics</p>
          </div>
          <button
            onClick={fetchStats}
            className="flex items-center gap-2 px-4 py-2 bg-white border border-gray-300 rounded-lg hover:bg-gray-50"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Stats Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <StatCard
            title="Total Sessions"
            value={stats?.sessions.total || 0}
            subtitle={`${stats?.sessions.active_24h || 0} active today`}
            icon={<Users className="w-6 h-6" />}
            color="blue"
          />
          <StatCard
            title="Messages Today"
            value={stats?.messages.today || 0}
            subtitle={`${stats?.messages.total || 0} total`}
            icon={<MessageSquare className="w-6 h-6" />}
            color="green"
          />
          <StatCard
            title="Pending Escalations"
            value={stats?.escalations.pending || 0}
            subtitle="Needs attention"
            icon={<AlertTriangle className="w-6 h-6" />}
            color="orange"
          />
          <StatCard
            title="Avg Confidence"
            value={`${stats?.performance.avg_confidence_7d || 0}%`}
            subtitle="Last 7 days"
            icon={<TrendingUp className="w-6 h-6" />}
            color="purple"
          />
        </div>

        {/* Knowledge Base Stats */}
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-8">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">
            Knowledge Base
          </h2>
          <div className="grid grid-cols-3 gap-6">
            <div className="text-center">
              <p className="text-3xl font-bold text-primary-600">
                {stats?.knowledge_base.faqs || 0}
              </p>
              <p className="text-gray-500">FAQs</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-primary-600">
                {stats?.knowledge_base.documents || 0}
              </p>
              <p className="text-gray-500">Documents</p>
            </div>
            <div className="text-center">
              <p className="text-3xl font-bold text-primary-600">
                {stats?.knowledge_base.vector_chunks || 0}
              </p>
              <p className="text-gray-500">Vector Chunks</p>
            </div>
          </div>
        </div>

        {/* Quick Links */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <QuickLink
            title="Manage FAQs"
            description="Add, edit, or remove FAQ entries"
            href="/docs#/FAQs"
          />
          <QuickLink
            title="Upload Documents"
            description="Upload PDFs and circulars"
            href="/docs#/Documents"
          />
          <QuickLink
            title="View Conversations"
            description="Review chat logs"
            href="/docs#/Admin"
          />
        </div>
      </div>
    </div>
  )
}

function StatCard({
  title,
  value,
  subtitle,
  icon,
  color,
}: {
  title: string
  value: string | number
  subtitle: string
  icon: React.ReactNode
  color: 'blue' | 'green' | 'orange' | 'purple'
}) {
  const colorClasses = {
    blue: 'bg-blue-50 text-blue-600',
    green: 'bg-green-50 text-green-600',
    orange: 'bg-orange-50 text-orange-600',
    purple: 'bg-purple-50 text-purple-600',
  }

  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-2 rounded-lg ${colorClasses[color]}`}>{icon}</div>
      </div>
      <p className="text-3xl font-bold text-gray-900">{value}</p>
      <p className="text-sm text-gray-500">{title}</p>
      <p className="text-xs text-gray-400 mt-1">{subtitle}</p>
    </div>
  )
}

function QuickLink({
  title,
  description,
  href,
}: {
  title: string
  description: string
  href: string
}) {
  return (
    <a
      href={href}
      className="block bg-white rounded-xl shadow-sm border border-gray-200 p-6 hover:shadow-md transition-shadow"
    >
      <h3 className="font-semibold text-gray-900 mb-1">{title}</h3>
      <p className="text-sm text-gray-500">{description}</p>
    </a>
  )
}
