import { useTranslation } from 'react-i18next';
import './LanguageSwitcher.css';

export function LanguageSwitcher() {
  const { i18n, t } = useTranslation();

  const changeLanguage = (lng: string) => {
    i18n.changeLanguage(lng);
  };

  return (
    <div className="language-switcher">
      <label htmlFor="language-select">{t('language.selectLanguage')}:</label>
      <select
        id="language-select"
        value={i18n.language}
        onChange={(e) => changeLanguage(e.target.value)}
        className="language-select"
      >
        <option value="fr">{t('language.french')}</option>
        <option value="en">{t('language.english')}</option>
      </select>
    </div>
  );
}
