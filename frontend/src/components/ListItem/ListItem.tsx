import cn from 'classnames'

import { Icon } from '../Icon'
import styles from './ListItem.module.scss'

interface ListItemProps {
  text?: React.ReactNode
  children?: React.ReactNode
  description?: React.ReactNode
  before?: React.ReactNode
  after?: React.ReactNode
  chevron?: boolean
  onClick?: () => void
  disabled?: boolean
  paddingY?: 10 | 6
}

export const ListItem = ({
  text,
  children,
  description,
  before,
  after,
  chevron,
  disabled,
  onClick,
  paddingY = 10,
}: ListItemProps) => {
  const handleClick = () => {
    if (onClick && !disabled) {
      onClick()
    }
  }

  return (
    <div
      className={cn(
        styles.container,
        onClick && styles.clickable,
        disabled && styles.disabled,
        paddingY && styles[`paddingY-${paddingY}`]
      )}
      onClick={handleClick}
    >
      <div className={styles.left}>
        {before || null}
        <div className={styles.content}>
          {text && <div>{text}</div>}
          {description && <div>{description}</div>}
          {children && children}
        </div>
      </div>
      <div className={styles.right}>
        {after || null}
        {chevron && <Icon name="chevron" />}
      </div>
    </div>
  )
}
