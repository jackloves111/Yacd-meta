import * as React from 'react';

import { fetchConfigs } from '~/api/configs';
import { BackendList } from '~/components/BackendList';
import { addClashAPIConfig, getClashAPIConfig } from '~/store/app';
import { State } from '~/store/types';
import { ClashAPIConfig } from '~/types';

import s0 from './APIConfig.module.scss';
import Button from './Button';
import Field from './Field';
import { connect } from './StateProvider';
import SvgYacd from './SvgYacd';

const { useState, useRef, useCallback, useEffect } = React;
const Ok = 0;

const mapState = (s: State) => ({
  apiConfig: getClashAPIConfig(s),
});

function APIConfig({ dispatch }) {
  const [baseURL, setBaseURL] = useState('');
  const [secret, setSecret] = useState('');
  const [errMsg, setErrMsg] = useState('');

  const userTouchedFlagRef = useRef(false);
  const contentEl = useRef(null);

  const handleInputOnChange = useCallback((e) => {
    userTouchedFlagRef.current = true;
    setErrMsg('');
    const target = e.target;
    const { name } = target;
    const value = target.value;
    switch (name) {
      case 'baseURL':
        setBaseURL(value);
        break;
      case 'secret':
        setSecret(value);
        break;
      default:
        throw new Error(`unknown input name ${name}`);
    }
  }, []);

  const onConfirm = useCallback(() => {
    let unconfirmedBaseURL = baseURL;
    if (unconfirmedBaseURL) {
      // 自动补全协议前缀
      if (!unconfirmedBaseURL.startsWith('http://') && !unconfirmedBaseURL.startsWith('https://')) {
        const protocol = window.location.protocol || 'http:';
        unconfirmedBaseURL = `${protocol}//${unconfirmedBaseURL}`;
      }
    }
    
    // 显示正在连接的提示
    setErrMsg('正在连接...');
    
    verify({ baseURL: unconfirmedBaseURL, secret }).then((ret) => {
      if (ret[0] !== Ok) {
        setErrMsg(ret[1]);
      } else {
        setErrMsg('');
        dispatch(addClashAPIConfig({ baseURL: unconfirmedBaseURL, secret }));
      }
    });
  }, [baseURL, secret, dispatch]);

  const handleContentOnKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (
        e.target instanceof Element &&
        (!e.target.tagName || e.target.tagName.toUpperCase() !== 'INPUT')
      ) {
        return;
      }
      if (e.key !== 'Enter') return;

      onConfirm();
    },
    [onConfirm]
  );

  useEffect(() => {
    // 设置默认的API URL，使用当前页面的主机名
    setBaseURL(`http://${window.location.hostname}:9090`);
    
    // 如果用户尝试使用自定义主机名（如classh），请确保该主机名可以被解析
    // 可能需要在hosts文件中添加对应的映射，或确保DNS服务器可以解析该主机名
  }, []);

  return (
    // eslint-disable-next-line jsx-a11y/no-static-element-interactions
    <div className={s0.root} ref={contentEl} onKeyDown={handleContentOnKeyDown}>
      <div className={s0.header}>
        <div className={s0.icon}>
          <SvgYacd width={160} height={160} stroke="var(--stroke)" />
        </div>
      </div>
      <div className={s0.body}>
        <div className={s0.hostnamePort}>
          <Field
            id="baseURL"
            name="baseURL"
            label="Clash API URL"
            type="text"
            placeholder={`http://${window.location.hostname}:9090`}
            value={baseURL}
            onChange={handleInputOnChange}
          />
          <Field
            id="secret"
            name="secret"
            label="密钥(默认留空)"
            value={secret}
            type="text"
            onChange={handleInputOnChange}
          />
        </div>
      </div>
      <div className={s0.error}>{errMsg ? errMsg : null}</div>
      <div className={s0.footer}>
        <Button label="Add" onClick={onConfirm} />
      </div>
      <div style={{ height: 20 }} />
      <BackendList />
    </div>
  );
}

export default connect(mapState)(APIConfig);

async function verify(apiConfig: ClashAPIConfig): Promise<[number, string?]> {
  try {
    // 检查URL格式
    try {
      new URL(apiConfig.baseURL);
    } catch (e) {
      return [1, '无效的URL格式'];
    }
    
    // 尝试连接API
    try {
      const res = await fetchConfigs(apiConfig);
      if (res.status > 399) {
        return [1, res.statusText];
      }
      return [Ok];
    } catch (e) {
      // 提供更详细的错误信息
      console.error('连接失败:', e);
      if (e instanceof TypeError && e.message.includes('Failed to fetch')) {
        return [1, '无法连接到服务器，请检查主机名是否正确或网络连接是否可用'];
      }
      return [1, '连接失败，请确认Clash服务正在运行且地址正确'];
    }
  } catch (e) {
    console.error('验证过程出错:', e);
    return [1, '验证过程出错'];
  }
}
