import { useEffect, useState } from 'react'
import { Card, Col, Row, Statistic, Spin, Alert, Select, Typography } from 'antd'
import {
  UserOutlined,
  CarOutlined,
  RiseOutlined,
  TeamOutlined,
} from '@ant-design/icons'
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from 'recharts'
import client from '../api/client'

const { Title } = Typography

interface Stats {
  total_users: number
  active_users: number
  leads_today: number
  leads_week: number
  leads_month: number
  top_brands: { brand: string; count: number }[]
  top_cities: { city: string; count: number }[]
}

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [period, setPeriod] = useState<'day' | 'week' | 'month'>('week')

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await client.get('/stats', { params: { period } })
        setStats(res.data)
      } catch {
        setError('Не удалось загрузить статистику')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [period])

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  const brandsData = stats?.top_brands?.slice(0, 10) ?? []
  const citiesData = stats?.top_cities?.slice(0, 10) ?? []

  return (
    <div>
      <Row gutter={[16, 16]} align="middle" style={{ marginBottom: 16 }}>
        <Col flex="auto">
          <Title level={4} style={{ margin: 0 }}>Обзор</Title>
        </Col>
        <Col>
          <Select
            value={period}
            onChange={setPeriod}
            style={{ width: 140 }}
            options={[
              { value: 'day', label: 'За сегодня' },
              { value: 'week', label: 'За неделю' },
              { value: 'month', label: 'За месяц' },
            ]}
          />
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Всего пользователей"
              value={stats?.total_users ?? 0}
              prefix={<TeamOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Активных пользователей"
              value={stats?.active_users ?? 0}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#52c41a' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Лидов за день"
              value={stats?.leads_today ?? 0}
              prefix={<CarOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title={period === 'week' ? 'Лидов за неделю' : period === 'month' ? 'Лидов за месяц' : 'Лидов за день'}
              value={period === 'week' ? (stats?.leads_week ?? 0) : period === 'month' ? (stats?.leads_month ?? 0) : (stats?.leads_today ?? 0)}
              prefix={<RiseOutlined />}
              valueStyle={{ color: '#1677ff' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 24 }}>
        <Col xs={24} lg={12}>
          <Card title="Топ марок автомобилей">
            {brandsData.length === 0 ? (
              <Typography.Text type="secondary">Нет данных</Typography.Text>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={brandsData} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="brand" angle={-40} textAnchor="end" interval={0} tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" name="Лидов" fill="#1677ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="Топ городов">
            {citiesData.length === 0 ? (
              <Typography.Text type="secondary">Нет данных</Typography.Text>
            ) : (
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={citiesData} margin={{ top: 5, right: 10, left: 0, bottom: 60 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="city" angle={-40} textAnchor="end" interval={0} tick={{ fontSize: 12 }} />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="count" name="Лидов" fill="#52c41a" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </Card>
        </Col>
      </Row>

    </div>
  )
}
