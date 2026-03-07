import { Box, Flex, Heading, Text, Stack } from '@chakra-ui/react';
import { motion } from 'framer-motion';
import { Search, Newspaper, Send } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import CTAButtons from './CTAButtons';

const MotionBox = motion.create(Box);
const MotionFlex = motion.create(Flex);
const MotionHeading = motion.create(Heading);
const MotionText = motion.create(Text);

interface TutorialSlide {
  number: string;
  icon: LucideIcon;
  title: string;
  steps: string[];
  mockupLabel: string;
}

const slides: TutorialSlide[] = [
  {
    number: '01',
    icon: Search,
    title: 'Analyze a Topic',
    steps: [
      'Ask about any topic, product, or trend',
      'We crawl Reddit, YouTube, and Amazon for real-time data',
      'Get a structured intelligence report with sentiment analysis',
    ],
    mockupLabel: 'Analysis Report',
  },
  {
    number: '02',
    icon: Newspaper,
    title: 'AI Daily Digest',
    steps: [
      'Open the AI Digest page from the sidebar',
      "View today's auto-generated intelligence briefing",
      'Share or export the digest as an image',
    ],
    mockupLabel: 'Daily Digest',
  },
  {
    number: '03',
    icon: Send,
    title: 'Connect Telegram',
    steps: [
      'Generate a bind code from Settings',
      'Send /bind YOUR_CODE to @SmIA_bot on Telegram',
      'Get analysis and digests delivered straight to Telegram',
    ],
    mockupLabel: 'Telegram Bot',
  },
];

export default function TutorialSection() {
  return (
    <Box as="section" aria-labelledby="tutorial-heading" bg="black" py={{ base: 16, md: 24 }}>
      <Box maxW="6xl" mx="auto" px={{ base: 6, md: 12 }}>
        {/* Section heading */}
        <MotionHeading
          id="tutorial-heading"
          as="h2"
          size="3xl"
          color="white"
          textAlign="center"
          mb={{ base: 16, md: 24 }}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-100px' }}
          transition={{ duration: 0.6 }}
        >
          How It{' '}
          <Text as="span" color="green.400">
            Works
          </Text>
        </MotionHeading>

        {/* Tutorial slides */}
        {slides.map((slide, index) => {
          const isReversed = index % 2 !== 0;
          const Icon = slide.icon;

          return (
            <MotionFlex
              key={slide.number}
              direction={{ base: 'column', md: isReversed ? 'row-reverse' : 'row' }}
              position="relative"
              minH={{ base: 'auto', md: '70vh' }}
              alignItems="center"
              gap={{ base: 8, md: 16 }}
              py={{ base: 12, md: 0 }}
              overflow="hidden"
              initial={{ opacity: 0 }}
              whileInView={{ opacity: 1 }}
              viewport={{ once: true, margin: '-100px' }}
              transition={{ duration: 0.5 }}
            >
              {/* Large faded step number watermark */}
              <Text
                position="absolute"
                top="50%"
                left={{ base: '50%', md: isReversed ? 'auto' : '5%' }}
                right={{ base: 'auto', md: isReversed ? '5%' : 'auto' }}
                transform="translateY(-50%)"
                fontSize={{ base: '8rem', md: '12rem' }}
                fontWeight="bold"
                color="rgba(74, 222, 128, 0.06)"
                pointerEvents="none"
                userSelect="none"
                aria-hidden="true"
                display={{ base: 'none', md: 'block' }}
                lineHeight={1}
              >
                {slide.number}
              </Text>

              {/* Mockup side */}
              <MotionBox
                w="100%"
                maxW={{ base: '100%', md: '50%' }}
                initial={{ opacity: 0, x: isReversed ? 40 : -40 }}
                whileInView={{ opacity: 1, x: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: 0.1 }}
              >
                <Box
                  position="relative"
                  borderRadius="xl"
                  overflow="hidden"
                  bg="rgba(74, 222, 128, 0.05)"
                  border="1px solid rgba(74, 222, 128, 0.1)"
                  style={{ aspectRatio: '16 / 9' }}
                >
                  <Flex
                    position="absolute"
                    inset={0}
                    alignItems="center"
                    justifyContent="center"
                    direction="column"
                    gap={3}
                  >
                    <Icon size={32} color="#4a5568" />
                    <Text color="gray.600" fontSize="sm" fontWeight="medium">
                      {slide.mockupLabel}
                    </Text>
                  </Flex>
                </Box>
              </MotionBox>

              {/* Text side */}
              <MotionBox
                w="100%"
                maxW={{ base: '100%', md: '50%' }}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, margin: '-100px' }}
                transition={{ duration: 0.6, delay: 0.2 }}
              >
                <Stack
                  gap={5}
                  borderLeft="3px solid"
                  borderLeftColor="green.400"
                  pl={6}
                >
                  {/* Number badge + title */}
                  <Flex alignItems="center" gap={3}>
                    <Flex
                      w="36px"
                      h="36px"
                      borderRadius="full"
                      bg="green.400"
                      color="black"
                      alignItems="center"
                      justifyContent="center"
                      fontWeight="bold"
                      fontSize="sm"
                      flexShrink={0}
                    >
                      {index + 1}
                    </Flex>
                    <Flex alignItems="center" gap={2}>
                      <Icon size={20} color="#4ade80" />
                      <Heading size="xl" color="white">
                        {slide.title}
                      </Heading>
                    </Flex>
                  </Flex>

                  {/* Steps */}
                  <Stack as="ol" gap={3} pl={0} listStyleType="none">
                    {slide.steps.map((step, stepIndex) => (
                      <MotionText
                        as="li"
                        key={stepIndex}
                        color="gray.300"
                        fontSize="md"
                        lineHeight="1.7"
                        initial={{ opacity: 0, y: 10 }}
                        whileInView={{ opacity: 1, y: 0 }}
                        viewport={{ once: true }}
                        transition={{ duration: 0.4, delay: 0.3 + stepIndex * 0.1 }}
                      >
                        <Text as="span" color="green.400" fontWeight="semibold" mr={2}>
                          {stepIndex + 1}.
                        </Text>
                        {step}
                      </MotionText>
                    ))}
                  </Stack>
                </Stack>
              </MotionBox>
            </MotionFlex>
          );
        })}

        {/* Closing CTA */}
        <MotionBox
          textAlign="center"
          py={{ base: 16, md: 24 }}
          initial={{ opacity: 0, y: 30 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-50px' }}
          transition={{ duration: 0.6 }}
        >
          <Heading size="xl" color="white" mb={8}>
            Ready to get started?
          </Heading>
          <Flex justifyContent="center">
            <CTAButtons />
          </Flex>
        </MotionBox>
      </Box>
    </Box>
  );
}
