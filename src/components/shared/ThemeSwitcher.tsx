import { Tooltip } from '@reach/tooltip';
import * as React from 'react';
import { useTranslation } from 'react-i18next';

import { connect } from '~/components/StateProvider';
import { framerMotionResouce } from '~/misc/motion';
import { getTheme, switchTheme } from '~/store/app';
import { State } from '~/store/types';

import s from './ThemeSwitcher.module.scss';

export function ThemeSwitcherImpl({ theme, dispatch }) {
  const { t } = useTranslation();

  const themeIcon = React.useMemo(() => {
    switch (theme) {
      case 'dark':
        return <MoonA />;
      case 'auto':
        return <Auto />;
      case 'light':
        return <Sun />;
      default:
        console.assert(false, 'Unknown theme');
        return <Sun />;
    }
  }, [theme]);

  const onChange = React.useCallback(
    (e: React.ChangeEvent<HTMLSelectElement>) => dispatch(switchTheme(e.target.value)),
    [dispatch]
  );

  return (
    <Tooltip label={t('switch_theme')} aria-label={'switch theme'}>
      <div className={s.themeSwitchContainer}>
        <span className={s.iconWrapper}>{themeIcon}</span>
        <select onChange={onChange} value={theme}>
          <option value="light">Light</option>
          <option value="auto">Auto</option>
          <option value="dark">Dark</option>
        </select>
      </div>
    </Tooltip>
  );
}

function MoonA() {
  const module = framerMotionResouce.read();
  const motion = module.motion;
  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <motion.path
        d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"
        initial={{ rotate: -30 }}
        animate={{ rotate: 0 }}
        transition={{ duration: 0.7 }}
      />
    </svg>
  );
}

function Sun() {
  const module = framerMotionResouce.read();
  const motion = module.motion;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="5"></circle>
      <motion.g initial={{ scale: 0.7 }} animate={{ scale: 1 }} transition={{ duration: 0.5 }}>
        <line x1="12" y1="1" x2="12" y2="3"></line>
        <line x1="12" y1="21" x2="12" y2="23"></line>
        <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line>
        <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line>
        <line x1="1" y1="12" x2="3" y2="12"></line>
        <line x1="21" y1="12" x2="23" y2="12"></line>
        <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line>
        <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>
      </motion.g>
    </svg>
  );
}

function Auto() {
  const module = framerMotionResouce.read();
  const motion = module.motion;

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      width="20"
      height="20"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="11" />
      <clipPath id="cut-off-bottom">
        <motion.rect
          x="12"
          y="0"
          width="12"
          height="24"
          initial={{ rotate: -30 }}
          animate={{ rotate: 0 }}
          transition={{ duration: 0.7 }}
        />
      </clipPath>
      <circle cx="12" cy="12" r="6" clipPath="url(#cut-off-bottom)" fill="currentColor" />
    </svg>
  );
}

const mapState = (s: State) => ({ theme: getTheme(s) });
export const ThemeSwitcher = connect(mapState)(ThemeSwitcherImpl);
