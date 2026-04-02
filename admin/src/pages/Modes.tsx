import { useEffect, useState } from 'react'
import {
  Card,
  Radio,
  InputNumber,
  Button,
  Space,
  Typography,
  Alert,
  Spin,
  Table,
  Tag,
  App,
} from 'antd'
import type { TableColumnsType } from 'antd'
import { SaveOutlined } from '@ant-design/icons'
import dayjs from 'dayjs'
import client from '../api/client'

const { Title, Text } = Typography

type Mode = 'exclusive' | 'speed' | 'coverage'
type LeadDeliveryMode = 'pull_broadcast' | 'pull_exclusive'

interface Settings {
  mode: Mode
  speed_group_size: number
  lead_delivery_mode: LeadDeliveryMode
  updated_at: string | null
  updated_by: string | null
}

interface LogEntry {
  id: number
  mode: Mode
  speed_group_size: number
  updated_at: string
  updated_by: string
}

const modeLabels: Record<Mode, string> = {
  exclusive: 'Эксклюзив',
  speed: 'Скорость',
  coverage: 'Охват',
}

const modeColors: Record<Mode, string> = {
  exclusive: 'gold',
  speed: 'blue',
  coverage: 'green',
}

const modeDescriptions: Record<Mode, string> = {
  exclusive: 'Лид отправляется одному пользователю из очереди Redis (RPOP). Гарантирует эксклюзивность.',
  speed: 'Лид отправляется первым N пользователям, успевшим нажать «Открыть контакт» (SETNX lock).',
  coverage: 'Лид отправляется всем пользователям с limit_count ≥ 1 одновременно (broadcast).',
}

const logColumns: TableColumnsType<LogEntry> = [
  {
    title: 'Дата',
    dataIndex: 'updated_at',
    render: (v) => dayjs(v).format('DD.MM.YYYY HH:mm'),
    width: 160,
  },
  {
    title: 'Режим',
    dataIndex: 'mode',
    render: (v: Mode) => <Tag color={modeColors[v]}>{modeLabels[v]}</Tag>,
    width: 130,
  },
  {
    title: 'Размер группы',
    dataIndex: 'speed_group_size',
    width: 140,
    render: (v, row) => (row.mode === 'speed' ? v : '—'),
  },
  {
    title: 'Изменил',
    dataIndex: 'updated_by',
  },
]

const deliveryModeLabels: Record<LeadDeliveryMode, string> = {
  pull_broadcast: 'Всем (Broadcast)',
  pull_exclusive: 'Первому (Exclusive)',
}

const deliveryModeDescriptions: Record<LeadDeliveryMode, string> = {
  pull_broadcast: 'Новый лид уходит всем, кто нажал «Запустить ледокол» и у кого есть баланс.',
  pull_exclusive: 'Новый лид уходит только первому активному пользователю из очереди.',
}

export default function Modes() {
  const { message } = App.useApp()
  const [settings, setSettings] = useState<Settings | null>(null)
  const [mode, setMode] = useState<Mode>('exclusive')
  const [groupSize, setGroupSize] = useState<number>(5)
  const [deliveryMode, setDeliveryMode] = useState<LeadDeliveryMode>('pull_broadcast')
  const [saving, setSaving] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [log, setLog] = useState<LogEntry[]>([])

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await client.get('/settings')
        setSettings(res.data)
        setMode(res.data.mode)
        setGroupSize(res.data.speed_group_size ?? 5)
        setDeliveryMode(res.data.lead_delivery_mode ?? 'pull_broadcast')
        if (Array.isArray(res.data.log)) {
          setLog(res.data.log)
        }
      } catch {
        setError('Не удалось загрузить настройки')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleSave = async () => {
    setSaving(true)
    try {
      await client.put('/settings', {
        mode,
        speed_group_size: groupSize,
        lead_delivery_mode: deliveryMode,
      })
      message.success('Режим сохранён')
      setSettings((prev) =>
        prev ? { ...prev, mode, speed_group_size: groupSize, lead_delivery_mode: deliveryMode } : prev
      )
    } catch {
      message.error('Ошибка при сохранении')
    } finally {
      setSaving(false)
    }
  }

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  const hasChanges =
    settings &&
    (settings.mode !== mode ||
      settings.speed_group_size !== groupSize ||
      settings.lead_delivery_mode !== deliveryMode)

  return (
    <Space direction="vertical" size={24} style={{ width: '100%' }}>
      <Card title="Режим дистрибуции лидов">
        <Space direction="vertical" size={20} style={{ width: '100%' }}>
          <Radio.Group
            value={mode}
            onChange={(e) => setMode(e.target.value)}
            size="large"
          >
            <Space direction="vertical" size={12}>
              {(['exclusive', 'speed', 'coverage'] as Mode[]).map((m) => (
                <Radio key={m} value={m}>
                  <Space direction="vertical" size={2}>
                    <Tag color={modeColors[m]} style={{ fontSize: 14, padding: '2px 10px' }}>
                      {modeLabels[m]}
                    </Tag>
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {modeDescriptions[m]}
                    </Text>
                  </Space>
                </Radio>
              ))}
            </Space>
          </Radio.Group>

          {mode === 'speed' && (
            <div>
              <Text strong>Размер группы (N пользователей): </Text>
              <InputNumber
                min={1}
                max={100}
                value={groupSize}
                onChange={(v) => setGroupSize(v ?? 5)}
                style={{ marginLeft: 8, width: 100 }}
              />
              <br />
              <Text type="secondary" style={{ fontSize: 12 }}>
                Первые N пользователей, нажавших «Открыть контакт», получат лид.
              </Text>
            </div>
          )}

          <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: 20 }}>
            <Text strong style={{ fontSize: 14 }}>Режим доставки лидов (ледокол):</Text>
            <div style={{ marginTop: 8 }}>
              <Radio.Group
                value={deliveryMode}
                onChange={(e) => setDeliveryMode(e.target.value)}
                size="large"
              >
                <Space direction="vertical" size={12}>
                  {(['pull_broadcast', 'pull_exclusive'] as LeadDeliveryMode[]).map((dm) => (
                    <Radio key={dm} value={dm}>
                      <Space direction="vertical" size={2}>
                        <Text strong style={{ fontSize: 13 }}>{deliveryModeLabels[dm]}</Text>
                        <Text type="secondary" style={{ fontSize: 12 }}>
                          {deliveryModeDescriptions[dm]}
                        </Text>
                      </Space>
                    </Radio>
                  ))}
                </Space>
              </Radio.Group>
            </div>
          </div>

          <Button
            type="primary"
            icon={<SaveOutlined />}
            onClick={handleSave}
            loading={saving}
            disabled={!hasChanges}
          >
            Сохранить
          </Button>
        </Space>
      </Card>

      {log.length > 0 && (
        <Card title="Лог смен режима">
          <Table
            dataSource={log}
            columns={logColumns}
            rowKey="id"
            size="small"
            pagination={{ pageSize: 10 }}
          />
        </Card>
      )}

      {log.length === 0 && (
        <Card>
          <Title level={5} style={{ margin: 0, color: '#999' }}>
            История смен режима пуста
          </Title>
        </Card>
      )}
    </Space>
  )
}
