"""Jornadas do minijogo 404 no Chromium, sem APIs ou serviços externos."""
import unittest

import browser_text_safety as safety


class Game404Tests(safety.TextSafetyBrowser):
    def open_game(self):
        self.page.clock.install()
        self.page.goto(safety.ORIGIN + '/404.html')

    def start(self):
        self.open_game()
        self.page.locator('#play').click()

    def matching(self):
        return self.page.locator('.card:not(.matched)').evaluate_all("""els => {
            const first = els[0];
            return els.filter(e => e.dataset.pair === first.dataset.pair)
              .map(e => [...e.parentElement.children].indexOf(e));
        }""")

    def match(self):
        for index in self.matching():
            self.page.locator('.card').nth(index).click()

    def test_404_waits_for_start_and_uses_no_api(self):
        requests = []
        self.page.on('request', lambda req: requests.append(req.url))
        self.open_game()
        self.page.clock.fast_forward(30000)
        self.assertEqual(self.page.locator('#time').inner_text(), '1:15')
        self.assertTrue(self.page.locator('#board').evaluate('e => e.inert'))
        self.assertEqual(self.page.locator('.card').count(), 12)
        self.assertNotIn('Mochila', self.page.locator('.card').first.get_attribute('aria-label'))
        self.page.locator('#play').click()
        self.page.clock.fast_forward(2000)
        self.assertEqual(self.page.locator('#time').inner_text(), '1:13')
        self.assertTrue(all(url.startswith(safety.ORIGIN + '/') for url in requests))
        self.assertFalse(any('/api/' in url for url in requests))

    def test_404_matches_combo_bonus_next_phase_and_persistent_record(self):
        self.start()
        self.match()
        self.assertEqual(self.page.locator('#score').inner_text(), '100')
        self.assertEqual(self.page.locator('#time').inner_text(), '1:20')
        self.match()
        self.assertEqual(self.page.locator('#score').inner_text(), '300')
        for _ in range(4):
            self.match()
        self.assertIn('Tudo de volta', self.page.locator('#overlay-title').inner_text())
        self.assertEqual(self.page.locator('.matched').count(), 12)
        saved = self.page.evaluate("localStorage.getItem('etec-operacao-achados-recorde-v1')")
        self.assertGreater(int(saved), 1500)
        self.page.locator('#play').click()
        self.assertEqual(self.page.locator('#level').inner_text(), '02')
        self.assertEqual(self.page.locator('.card').count(), 16)
        self.assertEqual(self.page.locator('#hints').inner_text(), '2')
        for _ in range(8):
            self.match()
        self.page.locator('#play').click()
        self.assertEqual(self.page.locator('.card').count(), 20)
        self.assertEqual(self.page.locator('#level').inner_text(), '03')
        best = self.page.locator('#best').inner_text()
        self.page.reload()
        self.assertEqual(self.page.locator('#best').inner_text(), best)
        self.assertEqual(self.page.locator('#score').inner_text(), '0')

    def test_404_mismatch_locks_third_card_and_resets_combo(self):
        self.start()
        self.match()
        unmatched = self.page.locator('.card:not(.matched)').evaluate_all("""els => {
          const a=els[0], b=els.find(e=>e.dataset.pair!==a.dataset.pair);
          return [a,b,els.find(e=>e!==a&&e!==b)].map(e=>[...e.parentElement.children].indexOf(e));
        }""")
        for index in unmatched:
            self.page.locator('.card').nth(index).click()
        self.assertEqual(self.page.locator('.card.revealed:not(.matched)').count(), 2)
        self.page.clock.fast_forward(1100)
        self.assertEqual(self.page.locator('.card.revealed:not(.matched)').count(), 0)
        self.match()
        self.assertEqual(self.page.locator('#score').inner_text(), '200')

    def test_404_hints_are_limited_and_pause_cancels_pending_turn(self):
        self.start()
        for remaining in ['1', '0']:
            self.page.locator('#hint').click()
            self.assertEqual(self.page.locator('.card.revealed').count(), 12)
            self.assertEqual(self.page.locator('#hints').inner_text(), remaining)
            self.page.clock.fast_forward(1600)
            self.assertEqual(self.page.locator('.card.revealed').count(), 0)
        self.assertTrue(self.page.locator('#hint').is_disabled())
        self.page.locator('.card').first.click()
        self.page.keyboard.press('Escape')
        frozen = self.page.locator('#time').inner_text()
        self.page.clock.fast_forward(120000)
        self.assertEqual(self.page.locator('#time').inner_text(), frozen)
        self.assertEqual(self.page.locator('.card.revealed').count(), 0)
        self.assertTrue(self.page.locator('#board').evaluate('e=>e.inert'))
        self.page.locator('#play').click()
        self.match()
        self.assertEqual(self.page.locator('.matched').count(), 2)

    def test_404_tab_hidden_pauses_and_hint_can_be_interrupted(self):
        self.start()
        self.page.locator('#hint').click()
        self.page.evaluate("""() => {
          Object.defineProperty(document, 'hidden', {get:()=>true, configurable:true});
          document.dispatchEvent(new Event('visibilitychange'));
        }""")
        self.page.clock.fast_forward(100000)
        self.assertTrue(self.page.locator('#overlay').is_visible())
        self.assertIn('podem esperar', self.page.locator('#overlay-title').inner_text())
        self.page.evaluate("delete document.hidden")
        self.page.locator('#play').click()
        self.assertEqual(self.page.locator('.card.revealed').count(), 0)
        self.assertFalse(self.page.locator('#hint').is_disabled())
        self.match()

    def test_404_timeout_clears_hint_and_restarts_from_phase_one(self):
        self.start()
        self.match()
        self.page.clock.fast_forward(79000)
        self.page.locator('#hint').click()
        self.page.clock.fast_forward(1200)
        self.assertEqual(self.page.locator('#time').inner_text(), '0:00')
        self.assertIn('Quase lá', self.page.locator('#overlay-title').inner_text())
        self.assertEqual(self.page.locator('.card.revealed:not(.matched)').count(), 0)
        self.page.locator('#play').click()
        self.page.clock.fast_forward(2000)
        self.assertEqual(self.page.locator('#level').inner_text(), '01')
        self.assertEqual(self.page.locator('#score').inner_text(), '0')
        self.assertEqual(self.page.locator('#time').inner_text(), '1:13')
        self.assertEqual(self.page.locator('.card.revealed').count(), 0)

    def test_404_keyboard_reduced_motion_and_touch_layouts(self):
        self.page.emulate_media(reduced_motion='reduce')
        self.start()
        self.assertTrue(self.page.locator('.card').first.evaluate('e=>e===document.activeElement'))
        self.page.keyboard.press('ArrowRight')
        self.assertTrue(self.page.locator('.card').nth(1).evaluate('e=>e===document.activeElement'))
        self.page.keyboard.press('Enter')
        self.assertTrue(self.page.locator('.card').nth(1).evaluate("e=>e.classList.contains('revealed')"))
        self.assertEqual(self.page.locator('.card-inner').first.evaluate('e=>getComputedStyle(e).transitionDuration'), '0s')
        other = self.page.locator('.card').evaluate_all("""els=>els.findIndex((e,i)=>
          i!==1 && e.dataset.pair===els[1].dataset.pair)""")
        self.page.locator('.card').nth(other).focus()
        self.page.keyboard.press('Space')
        self.assertEqual(self.page.locator('.matched').count(), 2)
        self.assertTrue(self.page.evaluate("document.activeElement.matches('.card:not(:disabled)')"))
        self.page.keyboard.press('Escape')
        for width in [320, 375, 390, 768, 1440, 1920]:
            self.page.set_viewport_size({'width': width, 'height': 900})
            self.assertLessEqual(self.page.evaluate('document.documentElement.scrollWidth'), width)
            self.assertTrue(self.page.locator('.exit-link').is_visible())

    def test_404_unavailable_storage_does_not_break_game(self):
        self.page.add_init_script("Storage.prototype.getItem=()=>{throw Error('blocked')}; Storage.prototype.setItem=()=>{throw Error('blocked')}")
        self.start()
        self.match()
        self.assertEqual(self.page.locator('#score').inner_text(), '100')
        self.assertIn('100', self.page.locator('#best').inner_text())

    def test_404_touch_and_no_javascript_still_allow_return_to_portal(self):
        self.open_game()
        context = self.browser.new_context(has_touch=True, is_mobile=True, viewport={'width': 390, 'height': 844})
        context.route('**/*', self.route)
        page = context.new_page()
        try:
            page.goto(safety.ORIGIN + '/404.html')
            page.locator('#play').tap()
            page.locator('.card').first.tap()
            self.assertEqual(page.locator('.card.revealed').count(), 1)
            page.locator('#pause').tap()
            self.assertTrue(page.locator('#overlay').is_visible())
        finally:
            context.close()
        context = self.browser.new_context(java_script_enabled=False)
        context.route('**/*', self.route)
        page = context.new_page()
        try:
            page.goto(safety.ORIGIN + '/404.html')
            self.assertTrue(page.locator('.no-script a[href="/"]').is_visible())
            self.assertTrue(page.locator('.exit-link').is_visible())
        finally:
            context.close()


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(Game404Tests(name) for name in loader.getTestCaseNames(Game404Tests) if name.startswith('test_404_'))


if __name__ == '__main__':
    unittest.main()
