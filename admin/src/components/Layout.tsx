import {
  Layout as AntLayout,
  Menu,
  Button,
  Typography,
  Avatar,
  Flex,
} from 'antd'
import {
  DashboardOutlined,
  SettingOutlined,
  TeamOutlined,
  BarChartOutlined,
  LogoutOutlined,
  CarOutlined,
  UnorderedListOutlined,
  AuditOutlined,
} from '@ant-design/icons'
import { useNavigate, useLocation, Outlet } from 'react-router-dom'
import { useAuthStore } from '../store/auth'

const { Sider, Header, Content } = AntLayout
const { Text } = Typography

const menuItems = [
  { key: '/', icon: <DashboardOutlined />, label: 'Dashboard' },
  { key: '/moderation', icon: <AuditOutlined />, label: 'Модерация' },
  { key: '/leads', icon: <UnorderedListOutlined />, label: 'Лиды' },
  { key: '/modes', icon: <SettingOutlined />, label: 'Режимы' },
  { key: '/users', icon: <TeamOutlined />, label: 'Пользователи' },
  { key: '/analytics', icon: <BarChartOutlined />, label: 'Аналитика' },
]

export default function AppLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const logout = useAuthStore((s) => s.logout)

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <AntLayout style={{ minHeight: '100vh' }}>
      <Sider
        theme="dark"
        width={220}
        style={{ position: 'fixed', height: '100vh', left: 0, top: 0, zIndex: 100 }}
      >
        <Flex
          align="center"
          gap={10}
          style={{ padding: '20px 24px 16px', borderBottom: '1px solid rgba(255,255,255,0.08)' }}
        >
          <Avatar icon={<CarOutlined />} style={{ background: '#1677ff', flexShrink: 0 }} />
          <Text strong style={{ color: '#fff', fontSize: 16 }}>
            Авто-Лид
          </Text>
        </Flex>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[location.pathname]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
          style={{ marginTop: 8, flex: 1, borderRight: 0 }}
        />
        <div style={{ position: 'absolute', bottom: 0, width: '100%', padding: '16px 12px', borderTop: '1px solid rgba(255,255,255,0.08)' }}>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            style={{ color: 'rgba(255,255,255,0.65)', width: '100%', textAlign: 'left' }}
          >
            Выйти
          </Button>
        </div>
      </Sider>

      <AntLayout style={{ marginLeft: 220 }}>
        <Header
          style={{
            background: '#fff',
            padding: '0 24px',
            borderBottom: '1px solid #f0f0f0',
            display: 'flex',
            alignItems: 'center',
          }}
        >
          <Text style={{ fontSize: 18, fontWeight: 600 }}>
            {menuItems.find((m) => m.key === location.pathname)?.label ?? 'Авто-Лид'}
          </Text>
        </Header>
        <Content style={{ padding: 24, background: '#f5f5f5', minHeight: 'calc(100vh - 64px)' }}>
          <Outlet />
        </Content>
      </AntLayout>
    </AntLayout>
  )
}
