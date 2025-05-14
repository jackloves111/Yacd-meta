import * as React from 'react';
import { useTranslation } from 'react-i18next';
import ContentHeader from '~/components/ContentHeader';
import useRemainingViewPortHeight from '~/hooks/useRemainingViewPortHeight';
import { connect } from '~/components/StateProvider';
import { State } from '~/store/types';

function Logs() {
  const [refLogsContainer, containerHeight] = useRemainingViewPortHeight();
  const { t } = useTranslation();

  const iframeStyle = {
    width: '100%',
    height: `${containerHeight * 1}px`,
    border: 'none',
  };

  return (
    <div>
      <ContentHeader title={t('订阅')} />
      <div ref={refLogsContainer}>
        <iframe 
          src="https://0.0.0.0:7888/" 
          style={iframeStyle} 
          title="订阅"
        />
      </div>
    </div>
  );
}

const mapState = (s: State) => ({});

export default connect(mapState)(Logs);
