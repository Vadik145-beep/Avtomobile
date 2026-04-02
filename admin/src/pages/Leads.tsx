import { useEffect, useState } from 'react'
import {
  Table,
  Tag,
  Typography,
  Spin,
  Alert,
  Space,
  Tooltip,
  Button,
  Popconfirm,
  message,
  Modal,
  Form,
  Input,
  Select,
  Switch,
} from 'antd'
import { DeleteOutlined, PlusOutlined } from '@ant-design/icons'
import type { TableColumnsType } from 'antd'
import dayjs from 'dayjs'
import client from '../api/client'

const { Text } = Typography

interface DeliveryInfo {
  status: 'sent' | 'opened' | 'blocked'
  username: string | null
  first_name: string | null
  telegram_id: number
  opened_at: string | null
}

interface LeadAdminOut {
  id: number
  call_id: string | null
  client_name: string | null
  country_origin: string | null
  timing: string | null
  city: string | null
  phone: string | null
  created_at: string
  distribution_mode: string
  is_test: boolean
  deliveries: DeliveryInfo[]
}

function getBuyerLabel(d: DeliveryInfo): string {
  if (d.username) return `@${d.username}`
  if (d.first_name) return d.first_name
  return `tg:${d.telegram_id}`
}

function LeadStatus({ deliveries }: { deliveries: DeliveryInfo[] }) {
  if (deliveries.length === 0) {
    return <Tag color="default">Не отправлен</Tag>
  }

  const opened = deliveries.filter((d) => d.status === 'opened')
  const sent = deliveries.filter((d) => d.status === 'sent')

  if (opened.length > 0) {
    return (
      <Space direction="vertical" size={2}>
        <Tag color="success">Открыт</Tag>
        {opened.map((d) => (
          <Tooltip
            key={d.telegram_id}
            title={d.opened_at ? `Открыт: ${dayjs(d.opened_at).format('DD.MM.YYYY HH:mm')}` : ''}
          >
            <Text style={{ fontSize: 12, color: '#52c41a' }}>
              {getBuyerLabel(d)}
            </Text>
          </Tooltip>
        ))}
      </Space>
    )
  }

  return (
    <Space direction="vertical" size={2}>
      <Tag color="processing">Отправлен</Tag>
      {sent.map((d) => (
        <Text key={d.telegram_id} style={{ fontSize: 12, color: '#1677ff' }}>
          {getBuyerLabel(d)}
        </Text>
      ))}
    </Space>
  )
}

interface LeadCreateValues {
  phone: string
  client_name?: string
  country_origin?: string
  timing?: string
  city?: string
  summary?: string
  distribution_mode: 'coverage' | 'speed' | 'exclusive'
  is_test: boolean
}

export default function Leads() {
  const [leads, setLeads] = useState<LeadAdminOut[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deletingIds, setDeletingIds] = useState<Set<number>>(new Set())
  const [modalOpen, setModalOpen] = useState(false)
  const [formLoading, setFormLoading] = useState(false)
  const [form] = Form.useForm<LeadCreateValues>()

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      setError(null)
      try {
        const res = await client.get('/leads', { params: { limit: 200 } })
        setLeads(res.data)
      } catch {
        setError('Не удалось загрузить лиды')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const handleCreate = async (values: LeadCreateValues) => {
    setFormLoading(true)
    try {
      const res = await client.post('/leads', values)
      setLeads((prev) => [res.data, ...prev])
      message.success('Лид добавлен')
      setModalOpen(false)
      form.resetFields()
    } catch {
      message.error('Не удалось добавить лид')
    } finally {
      setFormLoading(false)
    }
  }

  const handleDelete = async (id: number) => {
    setDeletingIds((prev) => new Set(prev).add(id))
    try {
      await client.delete(`/leads/${id}`)
      setLeads((prev) => prev.filter((l) => l.id !== id))
      message.success('Лид удалён')
    } catch {
      message.error('Не удалось удалить лид')
    } finally {
      setDeletingIds((prev) => {
        const next = new Set(prev)
        next.delete(id)
        return next
      })
    }
  }

  const columns: TableColumnsType<LeadAdminOut> = [
    {
      title: 'Дата',
      dataIndex: 'created_at',
      width: 140,
      render: (v: string) => dayjs(v).format('DD.MM.YYYY HH:mm'),
      sorter: (a, b) => dayjs(a.created_at).unix() - dayjs(b.created_at).unix(),
      defaultSortOrder: 'descend',
    },
    {
      title: 'Клиент / Город',
      width: 180,
      render: (_: unknown, r: LeadAdminOut) => (
        <Space direction="vertical" size={0}>
          <Space size={4}>
            <Text strong>{r.client_name || '—'}</Text>
            {r.is_test && <Tag color="red" style={{ marginLeft: 4 }}>Тест</Tag>}
          </Space>
          <Text type="secondary" style={{ fontSize: 12 }}>{r.city || '—'}</Text>
        </Space>
      ),
      filters: [
        { text: 'Только тесты', value: 'test' },
        { text: 'Только боевые', value: 'real' },
      ],
      onFilter: (value, record) => {
        if (value === 'test') return record.is_test
        if (value === 'real') return !record.is_test
        return true
      },
    },
    {
      title: 'Страна / Сроки',
      width: 150,
      render: (_: unknown, r: LeadAdminOut) => (
        <Space direction="vertical" size={0}>
          <Text>{r.country_origin || '—'}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>{r.timing || '—'}</Text>
        </Space>
      ),
    },
    {
      title: 'Телефон',
      dataIndex: 'phone',
      width: 150,
      render: (v: string | null) => v ? <Text copyable>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: 'Режим',
      dataIndex: 'distribution_mode',
      width: 110,
      render: (v: string) => {
        const map: Record<string, { label: string; color: string }> = {
          coverage: { label: 'Охват', color: 'blue' },
          speed: { label: 'Скорость', color: 'orange' },
          exclusive: { label: 'Эксклюзив', color: 'purple' },
        }
        const item = map[v] ?? { label: v, color: 'default' }
        return <Tag color={item.color}>{item.label}</Tag>
      },
      filters: [
        { text: 'Охват', value: 'coverage' },
        { text: 'Скорость', value: 'speed' },
        { text: 'Эксклюзив', value: 'exclusive' },
      ],
      onFilter: (value, record) => record.distribution_mode === value,
    },
    {
      title: 'Статус / Покупатель',
      width: 200,
      render: (_: unknown, r: LeadAdminOut) => <LeadStatus deliveries={r.deliveries} />,
      filters: [
        { text: 'Не отправлен', value: 'none' },
        { text: 'Отправлен', value: 'sent' },
        { text: 'Открыт', value: 'opened' },
      ],
      onFilter: (value, record) => {
        if (value === 'none') return record.deliveries.length === 0
        if (value === 'opened') return record.deliveries.some((d) => d.status === 'opened')
        if (value === 'sent') return record.deliveries.length > 0 && !record.deliveries.some((d) => d.status === 'opened')
        return true
      },
    },
    {
      title: '',
      key: 'actions',
      width: 60,
      render: (_: unknown, r: LeadAdminOut) => (
        <Popconfirm
          title="Удалить лид?"
          description="Это действие нельзя отменить"
          okText="Удалить"
          cancelText="Отмена"
          okButtonProps={{ danger: true }}
          onConfirm={() => handleDelete(r.id)}
        >
          <Button
            danger
            type="text"
            icon={<DeleteOutlined />}
            loading={deletingIds.has(r.id)}
          />
        </Popconfirm>
      ),
    },
  ]

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '80px auto' }} />
  if (error) return <Alert type="error" message={error} />

  return (
    <>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          type="primary"
          icon={<PlusOutlined />}
          onClick={() => setModalOpen(true)}
        >
          Добавить лид
        </Button>
      </div>

      <Table
        dataSource={leads}
        columns={columns}
        rowKey="id"
        size="middle"
        pagination={{ pageSize: 20, showSizeChanger: true, showTotal: (t) => `Всего: ${t}` }}
        locale={{ emptyText: 'Лидов пока нет' }}
      />

      <Modal
        title="Добавить лид вручную"
        open={modalOpen}
        onCancel={() => { setModalOpen(false); form.resetFields() }}
        onOk={() => form.submit()}
        okText="Добавить"
        cancelText="Отмена"
        confirmLoading={formLoading}
        destroyOnClose
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleCreate}
          initialValues={{ distribution_mode: 'coverage', is_test: false }}
        >
          <Form.Item
            name="phone"
            label="Телефон"
            rules={[{ required: true, message: 'Введите номер телефона' }]}
          >
            <Input placeholder="+7 999 123 45 67" />
          </Form.Item>
          <Form.Item name="client_name" label="Имя клиента">
            <Input placeholder="Иван" />
          </Form.Item>
          <Form.Item name="country_origin" label="Страна">
            <Select
              allowClear
              placeholder="Выберите страну"
              options={[
                { value: 'Корея', label: 'Корея' },
                { value: 'Китай', label: 'Китай' },
              ]}
            />
          </Form.Item>
          <Form.Item name="city" label="Город">
            <Input placeholder="Москва" />
          </Form.Item>
          <Form.Item name="timing" label="Сроки">
            <Input placeholder="1-2 месяца" />
          </Form.Item>
          <Form.Item name="summary" label="Описание / транскрипт">
            <Input.TextArea rows={3} placeholder="Краткое описание обращения" />
          </Form.Item>
          <Form.Item name="distribution_mode" label="Режим дистрибуции">
            <Select
              options={[
                { value: 'coverage', label: 'Охват' },
                { value: 'speed', label: 'Скорость' },
                { value: 'exclusive', label: 'Эксклюзив' },
              ]}
            />
          </Form.Item>
          <Form.Item name="is_test" label="Тестовый лид" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </>
  )
}
