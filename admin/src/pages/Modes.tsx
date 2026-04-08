import { useEffect, useState } from 'react'
import {
  Card,
  Space,
  Typography,
  Alert,
  Spin,
  Button,
  message,
  Row,
  Col,
} from 'antd'
import { TeamOutlined, UserOutlined, CheckCircleFilled, ReloadOutlined } from '@ant-design/icons'
import client from '../api/client'

const { Title, Text, Paragraph } = Typography

type LeadDeliveryMode = 'pull_broadcast' | 'pull_exclusive'

interface Settings {
  lead_delivery_mode: LeadDeliveryMode
  updated_by: number | null
}

const MODES: {
  key: LeadDeliveryMode
  label: string
  description: string
  icon: React.ReactNode
  color: string
  borderColor: string
}[] = [
  {
    key: 'pull_broadcast',
    label: 'Всем',
    description: 'Лид отправляется всем активным пользователям, у которых есть баланс. Каждый получает уведомление одновременно.',
    icon: <TeamOutlined style={{ fontSize: 36 }} />,
    color: '#1677ff',
    borderColor: '#1677ff',
  },
  {
    key: 'pull_exclusive',
    label: 'Одному',
    description: 'Лид отправляется только тому пользователю, до которого дошла очередь. Одноразовый — следующий лид уйдёт следующему.',
    icon: <UserOutlined style={{ fontSize: 36 }} />,
    color: '#52c41a',
    borderColor: '#52c41a',
  },
]

export default function Modes() {
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [resettingQueue, setResettingQueue] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [current, setCurrent] = useState<LeadDeliveryMode>('pull_broadcast')

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await client.get<Settings>('/settings')
      setCurrent(res.data.lead_delivery_mode)
    } catch {
      setError('Не удалось загрузить настройки')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  const handleResetQueue = async () => {
    setResettingQueue(true)
    try {
      await client.post('/queue/reset')
      message.success('Очередь пересброшена')
    } catch {
      message.error('Не удалось пересбросить очередь')
    } finally {
      setResettingQueue(false)
    }
  }

  const handleSelect = async (mode: LeadDeliveryMode) => {
    if (mode === current || saving) return
    setSaving(true)
    try {
      const res = await client.put<Settings>('/settings', { lead_delivery_mode: mode })
      setCurrent(res.data.lead_delivery_mode)
      message.success('Режим обновлён')
    } catch {
      message.error('Не удалось сохранить режим')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} action={<Button size="small" onClick={load}>Повторить</Button>} />

  return (
    <Space direction="vertical" size={24} style={{ width: '100%' }}>
      <Card>
        <Title level={4} style={{ marginBottom: 4 }}>Режим раздачи лидов</Title>
        <Text type="secondary">
          Выберите, как новые лиды будут распределяться между пользователями.
        </Text>
      </Card>

      <Row gutter={24}>
        {MODES.map((mode) => {
          const isActive = current === mode.key
          return (
            <Col xs={24} md={12} key={mode.key}>
              <Card
                hoverable={!isActive}
                onClick={() => handleSelect(mode.key)}
                style={{
                  borderWidth: 2,
                  borderColor: isActive ? mode.borderColor : '#d9d9d9',
                  cursor: isActive ? 'default' : 'pointer',
                  transition: 'border-color 0.2s',
                  height: '100%',
                }}
                styles={{ body: { padding: 28 } }}
              >
                <Space direction="vertical" size={16} style={{ width: '100%' }}>
                  <Space size={16} align="start">
                    <span style={{ color: isActive ? mode.color : '#bfbfbf' }}>
                      {mode.icon}
                    </span>
                    <div>
                      <Space align="center" size={8}>
                        <Title level={3} style={{ margin: 0, color: isActive ? mode.color : undefined }}>
                          {mode.label}
                        </Title>
                        {isActive && (
                          <CheckCircleFilled style={{ color: mode.color, fontSize: 20 }} />
                        )}
                      </Space>
                      <Paragraph type="secondary" style={{ marginBottom: 0, marginTop: 4 }}>
                        {mode.description}
                      </Paragraph>
                    </div>
                  </Space>

                  <Button
                    type={isActive ? 'primary' : 'default'}
                    disabled={isActive}
                    loading={saving && current !== mode.key}
                    onClick={(e) => { e.stopPropagation(); handleSelect(mode.key) }}
                    style={{ width: '100%' }}
                  >
                    {isActive ? 'Активен' : 'Выбрать'}
                  </Button>
                  {isActive && mode.key === 'pull_exclusive' && (
                    <Button
                      icon={<ReloadOutlined />}
                      loading={resettingQueue}
                      onClick={(e) => { e.stopPropagation(); handleResetQueue() }}
                      style={{ width: '100%' }}
                    >
                      Пересбросить очередь
                    </Button>
                  )}
                </Space>
              </Card>
            </Col>
          )
        })}
      </Row>
    </Space>
  )
}
